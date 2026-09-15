package com.se.service;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.se.api.PythonServiceApi;
import com.se.dto.SearchResDto;
import com.se.dto.WebSocketDto;
import com.se.entity.*;
import com.se.serviceImpl.SearchServiceImpl;
import com.se.util.*;
import org.python.antlr.op.In;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Service;

import javax.validation.constraints.Null;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Service
public class SearchService implements SearchServiceImpl {
    @Autowired
    IndexUtil indexUtil;
    @Autowired
    SearchUtil searchUtil;

    @Autowired
    RedisUtil redisUtil;
    @Autowired
    MongoTemplate mongoTemplate;
    final int boostFactor = 10;// rank of title match is boosted by 2 for its term weights (tfidf)
    final int topResults = 50;// retrieve top 50 results
    final int MAX_CONTENT = 300; // max value of content length
    final String CUE_WORD_TITLE = "This is the search query given by the user:";
    final String CUE_WORD_BODY = ". Please generate a concise summary within 100 words based on both the query and the search results, focusing on the key information most relevant to the user's query. Strictly exclude any advertisement content from the summary. If the search results contain multiple languages, please generate the summary in the dominant language of the results. Organize the summary into short paragraphs with clear subheadings if applicable.";

    private ExecutorService executor = Executors.newFixedThreadPool(10);

    @Override
    public SearchResDto getSearchRes(String keywords){
        String keywordSet = String.join(" ", indexUtil.pretreatmentString(keywords));
//        System.out.println("正在提取"+keywordSet+"的token id。。。");
        String requestBody = "{\"content\":\""+keywordSet+"\"}";
        JSONObject originStems = PythonServiceApi.getPyServiceRes(requestBody,"http://localhost:8888/ordered_tokenize");
//        System.out.println("token id提取完毕");
        System.out.println("keywords: " + keywords + "   " + keywordSet + ", stems: " + originStems.toString());
//        System.out.println("正在提取短语。。。");
        JSONObject stems = searchUtil.extractPhrase(originStems.getJSONArray("TOKEN_ID").toArray(new String[0]));
//        System.out.println("短语提取完毕！");

        List<String> allTitleDocs = new ArrayList<>();
        List<String> allContentDocs = new ArrayList<>();
        Map<String, Float> queryTerms = new HashMap<>();    // store tfidf weights for terms across entire query (stems)
        Map<String, Integer> queryDfs = new HashMap<>();
        Map<String, Map<String, Float>> docsTerms;          // store tfidf weights for terms across ALL documents

        int queryTfMax = searchUtil.findMaxValue(stems);    // tf_max for query terms


//        System.out.println("正在查询索引数据库。。。");
        Query indexQuery = new Query(Criteria.where("_id").in(stems.keySet()));

        List<InvertIndex> titleDocList = mongoTemplate.find(indexQuery, InvertIndex.class, "title_index");
//        System.out.println("标题index查询到"+titleDocList.size()+"条");
        List<InvertIndex> contentDocList = mongoTemplate.find(indexQuery, InvertIndex.class, "content_index");
//        System.out.println("正文index查询到"+contentDocList.size()+"条");
        Query dfQuery = new Query();
        List<IndexDF> results = mongoTemplate.find(dfQuery, IndexDF.class, "stem_df");

        int N = 0;
        if (redisUtil.exists("file_num")) {
            N = (int) redisUtil.get("file_num");
        } else {
            List<Page> pagesList = mongoTemplate.find(dfQuery, Page.class, "forward_index");
            redisUtil.set("file_num", pagesList.size());
            N = pagesList.size();
        }

//        System.out.println("一共查到"+N+"条网页");
//
//        System.out.println("索引数据库查询完毕！");
        // step 1. Retrieve all relevant docs containing stems
        for (JSONObject.Entry<String, Object> stem : stems) {
            String key = stem.getKey();
            Set<String> allDocs = new HashSet<>();
//            String titleDocs = JDBMUtil.searchEntry("title_index", key);
            Query query=new Query();//创建query对象，用来添加过滤条件
            query.addCriteria(Criteria.where("_id").is(key));
            InvertIndex titleDocs = null;
            for (InvertIndex i : titleDocList) {
                if (i.getTokenId().equals(key)) {
                    titleDocs = i;
                }
            }
//            String contentDocs = JDBMUtil.searchEntry("content_index", key);
            InvertIndex contentDocs = null;
            for (InvertIndex i : contentDocList) {
                if (i.getTokenId().equals(key)) {
                    contentDocs = i;
                }
            }
//            System.out.println("--> in step 1, title docs: " + titleDocs + ", content docs: " + contentDocs);

            if(titleDocs != null){
                Map<String, Index> map = titleDocs.getIndexMap();
                for(String mapKey : map.keySet()){
                    allTitleDocs.add(map.get(mapKey).getUrl());
                    allDocs.add(map.get(mapKey).getUrl());
                }
            }
            if(contentDocs!= null){
                Map<String, Index> map = contentDocs.getIndexMap();
                for(String mapKey : map.keySet()){
                    allContentDocs.add(map.get(mapKey).getUrl());
                    allDocs.add(map.get(mapKey).getUrl());
                }
            }
            int queryDf = allDocs.size();               // df: length of title and content result arrays
            queryDfs.put(key, queryDf);
        }
//        System.out.println("--> after step 1, title docs: " + allTitleDocs + ", content docs: " + allContentDocs + ", query DFs: " + queryDfs + " ? " + allTitleDocs.size() + " ? " + allContentDocs.size());

        // step 2a. Compute tf idf of query, tf = stems, df = total no. of docs returned
        for (JSONObject.Entry<String, Object> stem : stems) {
            String key = stem.getKey();
            if ("ARTICLE_ID".equals(key)) {
                continue;
            }
            int queryTf = (int) stem.getValue();
            int queryDf = queryDfs.get(key);
            float queryTfidf = 0;

            if(queryDf > 0){
                float queryIdf = (float) (Math.log(N/(float)queryDf) / Math.log(2));
                queryTfidf = queryTf * queryIdf/ queryTfMax;
                if (key.contains("-")) {
                    int boostNum = (int) key.chars()
                            .filter(ch -> ch == '-')
                            .count();
                    queryTfidf *= (2*boostNum);
                }
            }

            queryTerms.put(key, queryTfidf);
        }
//        System.out.println("--> after step 2a, query terms: " + queryTerms);

//        System.out.println("正在计算TF*IDF。。。");
        // step 2b. Compute tf idf of documents (*** rank of title match is boosted here)
        Map<String, Map<String, Float>> titleDocsTerms = searchUtil.computeDocTfIdf(allTitleDocs, "title_tf", N, boostFactor, results);
        Map<String, Map<String, Float>> contentDocsTerms = searchUtil.computeDocTfIdf(allContentDocs, "content_tf", N, 1, results);
//        System.out.println("TF*IDF计算完毕！");

        // step 2c. Merge title docs weights and content docs weightings
        docsTerms = searchUtil.mergeDocsWeightings(titleDocsTerms, contentDocsTerms);
//        System.out.println("--> after step 2b merging, docs tfidf: " + docsTerms + ", length: " + docsTerms.size());

//        System.out.println("正在计算相似度。。。");
        // step 3. Compute cosine similarity between query and each documents
        Map<String, Float> docsSimilarity = new HashMap<>();
        for (Map.Entry<String, Map<String, Float>> docTerm : docsTerms.entrySet()) {
            String key = docTerm.getKey();
            Map<String, Float> docWeights = docTerm.getValue();
            float similarity = searchUtil.computeCosineSimilarity(queryTerms, docWeights);
            docsSimilarity.put(key, similarity);
        }
//        System.out.println("--> after step 3, docs similarity: " + docsSimilarity + ", length: " + docsSimilarity.size());

        // step 4. Rank and filter the similarities
        List<Map.Entry<String, Float>> sortedResults = searchUtil.getTopResults(docsSimilarity, topResults);
        Set<String> urlSet = new HashSet<>();
        for(Map.Entry<String, Float> result : sortedResults) {
            String key = result.getKey();
            urlSet.add(key);
        }
//        System.out.println("相似度计算完毕！");
//        System.out.println("正在生成结果集合！");

        Query query=new Query();//创建query对象，用来添加过滤条件
        query.addCriteria(Criteria.where("url").in(urlSet));
        List<Page> docResultList = mongoTemplate.find(query, Page.class, "forward_index");
        Map<String, Page> pageQueryMap = new HashMap<>();
        for (Page p : docResultList) {
            pageQueryMap.put(p.getUrl(), p);
        }
        // step 5. Create corresponding DTO
        SearchResDto res = new SearchResDto();
        int i = 0;
        for(Map.Entry<String, Float> result : sortedResults){
            String key = result.getKey();

//            String docResult = JDBMUtil.searchEntry("forward_index", key);
            Page docResult = pageQueryMap.get(key);
            if (docResult==null) {
                continue;
            }
            JSONObject docJSON = new JSONObject(docResult);
            String url = docJSON.getStr("url").replace('$','.');
            String title = docJSON.getStr("title");
            float score = sortedResults.get(i).getValue();
            String content = docResult.getContent();
            if (content.length()>MAX_CONTENT) {
                content = content.substring(0,MAX_CONTENT);
            }
            Set<IndexDF> keywordsFrequency = new HashSet<>();
            JSONObject contentTF = docResult.getContent_tf();
            JSONObject titleTF = docResult.getTitle_tf();

            Map<String, IndexDF> keywordsMap = new HashMap<>();
            // count keywords freq in content and title
            countKeywordsFreq(stems, contentTF, keywordsMap);

            countKeywordsFreq(stems, titleTF, keywordsMap);

            for (String tokenId : keywordsMap.keySet()) {
                keywordsFrequency.add(keywordsMap.get(tokenId));
            }

            res.addResults(url, title, score, content,docResult.getParentLink(),docResult.getChildrenLink(),keywordsFrequency, docResult.getIcon(),docResult.getImg());

            i++;
        }

        Set<String> keywordsTokenId = new HashSet<>();
        keywordsTokenId.addAll(stems.keySet());

        res.setKeywordsTokenId(keywordsTokenId);

        // handle LLM conclusion
        executor.submit(() -> {
            List<Message> topList = new ArrayList<>();
            List<SearchResult> resResults= res.getResults();
            final int CONCLUSION_NUM = 5;
            int j = 0;
            StringBuilder msgContent = new StringBuilder(CUE_WORD_TITLE+keywords+CUE_WORD_BODY);
            for (SearchResult result : resResults) {
                msgContent.append(j).append("、title:").append(result.getTitle()).append(" main body:").append(result.getContent());
                j++;
                if (j > CONCLUSION_NUM) {
                    break;
                }
            }

            String inputAI = msgContent.toString().replace("#", " ");
            topList.add(new Message("user", inputAI));
            String origin = JSONUtil.parseArray(topList).toString();
            JSONObject AIConclusion = PythonServiceApi.getPyServiceRes(origin,"http://localhost:8888/chat_with_AI");
            try {
                JSONObject resJson = new JSONObject();
                resJson.set("msg", (String) AIConclusion.get("content"));
                WebSocketDto webSocketDto = new WebSocketDto(1,resJson);
                WebSocketServer.sendInfo(JSONUtil.toJsonStr(webSocketDto));
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        });

        // handle related words
        executor.submit(() -> {
            String origin = "{\"content\":\""+keywordSet+"\"}";
            JSONObject relatedWords = PythonServiceApi.getPyServiceRes(origin, "http://localhost:8888/get_related_words");
            WebSocketDto webSocketDto = new WebSocketDto(0,relatedWords);
            try {
                WebSocketServer.sendInfo(JSONUtil.toJsonStr(webSocketDto));
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        });

        System.out.println("done！");

        return res;
    }

    private void countKeywordsFreq(JSONObject stems, JSONObject contentTF, Map<String, IndexDF> keywordsMap) {
        if (contentTF!=null) {
            for (String contentTFKey : contentTF.keySet()) {
                if (stems.containsKey(contentTFKey)) {
                    if (keywordsMap.containsKey(contentTFKey)) {
                        IndexDF keywordIndexDf = keywordsMap.get(contentTFKey);;
                        keywordIndexDf.setDf(keywordIndexDf.getDf()+(Integer) contentTF.get(contentTFKey));
                        keywordsMap.put(contentTFKey,keywordIndexDf);
                    } else {
                        keywordsMap.put(contentTFKey,new IndexDF(contentTFKey, (Integer) contentTF.get(contentTFKey)));
                    }
                }
            }
        }
    }
}
