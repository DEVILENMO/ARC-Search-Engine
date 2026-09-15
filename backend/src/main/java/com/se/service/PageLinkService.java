package com.se.service;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.se.api.PythonServiceApi;
import com.se.dto.WebSocketDto;
import com.se.dto.progressDto;
import com.se.entity.*;
import com.se.util.IndexUtil;
import com.se.util.ParserUtil;
import com.se.serviceImpl.PageLinkServiceImpl;
import com.se.global.UrlMap;
import com.se.util.SearchUtil;
import com.se.util.WebSocketServer;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.BulkOperations;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Update;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.LinkedBlockingQueue;

@Slf4j
@Service
public class PageLinkService implements PageLinkServiceImpl {
    @Autowired
    IndexUtil indexUtil;
    @Autowired
    MongoTemplate mongoTemplate;

    @Autowired
    SearchUtil searchUtil;
    /**
     * 根据起始节点爬取url，存储父子节点关系
     * @Param startUrl
     * **/
    @Override
    public void parsePageLink(String startUrl, int max_url, int max_depth) {
        try {
            DBInit();
            System.out.println("正在爬"+startUrl);
            String requestBody = "{\"start_url\":\""+startUrl+"\","+"\"max_depth\":\""+max_depth+"\","+"\"max_suburl\":\""+max_url+"\"}";
            JSONObject res = PythonServiceApi.getPyServiceRes(requestBody, "http://localhost:8888/crawler");
            Map<String, Page> urlWordsMap = new HashMap<>();
            for (String url : res.keySet()) {
                JSONObject pageValue = res.getJSONObject(url);
                Page page = new Page();
                page.setTitle(pageValue.getStr("title"));
                page.setContent(pageValue.getStr("content"));
                page.setIcon(pageValue.getStr("icon"));
                page.setUrl(url);
                page.setImg(pageValue.getStr("main_image"));

                Set<String> childLink = new HashSet<>();
                JSONArray childLinksJSON = pageValue.getJSONArray("sublinks");
                for (int i=0;i<childLinksJSON.size();i++) {
                    childLink.add(childLinksJSON.getStr(i));
                }
                page.setChildrenLink(childLink);
                urlWordsMap.put(url, page);
            }
            System.out.println("正在爬"+startUrl);
//            ParserUtil pu = new ParserUtil();
//            UrlMap urlMap = new UrlMap(0,new HashMap<>(),new LinkedBlockingQueue<>(),new HashSet<>());
//
//            urlMap.getPageLinkMap().put(startUrl, new PageLink(startUrl,"ROOT", new ArrayList<>()));
//            urlMap.getUrlQueue().offer(startUrl);
//
//            while (urlMap.getPageLinkMap().size()<max_url) {
//                if (!urlMap.getUrlQueue().isEmpty()) {
//                    String url = urlMap.getUrlQueue().poll();
//                    pu.extractLink(url, urlMap);
//                    log.info(String.valueOf(urlMap.getPageLinkMap().size()));
//                } else {
//                    break;
//                }
//            }
//
//            Map<String, PageLink> pageLinkMap = urlMap.getPageLinkMap();
//            for (String url : pageLinkMap.keySet()) {
//                mongoTemplate.save(pageLinkMap.get(url),"pageLink");
//            }
            System.out.println("url提取已完成！");
            parseWords(startUrl, urlWordsMap);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void parseWords(String startUrl, Map<String, Page> urlWordsMap) {
        int i=1;
        for (String key : urlWordsMap.keySet()) {
            try {
                Page page = urlWordsMap.get(key);
                // handle content inverted file
//                System.out.println("第"+i+"个任务：正在添加正文索引。。。");
                JSONObject content_tf_index = extractContentIndex(urlWordsMap.get(key).getTitle()+" "+urlWordsMap.get(key).getContent(),key);
                page.setId((String) content_tf_index.get("ARTICLE_ID"));
                content_tf_index.remove("ARTICLE_ID");
                saveChange("content_index",content_tf_index,key,page);
                page.setContent_tf(content_tf_index);
//                System.out.println("第"+i+"个任务：正文索引添加完毕！");

                // handle title inverted file
//                System.out.println("第"+i+"个任务：正在添加标题索引。。。");
                JSONObject title_tf_index = extractTitleIndex(urlWordsMap.get(key).getTitle(), key);
                saveChange("title_index", title_tf_index,key,page);
                page.setTitle_tf(title_tf_index);
//                System.out.println("第"+i+"个任务：标题索引添加完毕！");
//                System.out.println("第"+i+"个任务：正在插入文章正序索引");
                mongoTemplate.save(page, "forward_index");
//                System.out.println("第"+i+"个任务：文章正序索引插入完毕！");
                System.out.println("已完成"+i+"/"+urlWordsMap.keySet().size());
                i++;

                WebSocketDto webSocketDto = new WebSocketDto(2,new JSONObject(new progressDto(urlWordsMap.keySet().size(),i,startUrl)));
                WebSocketServer.sendInfo(JSONUtil.toJsonStr(webSocketDto));
            } catch (Exception e) {
                System.out.println("the"+i+"task fail,reason："+e.getMessage());
//                e.printStackTrace();
                i++;
            }
        }
        System.out.println("update phrases。。。");
        updatePhrases();
        System.out.println("phrases updated！");
        System.out.println("update parentLink。。。");
        updateParent();
        System.out.println("Finish！");
    }

    private boolean saveChange(String tableName, JSONObject stems, String url, Page page) {
        try {
            List<InvertIndex> invertIndexRes = new ArrayList<>();
            List<IndexDF> indexDFRes = new ArrayList<>();
            Query query = new Query();
            query.addCriteria(Criteria.where("_id").in(stems.keySet()));
            List<InvertIndex> invertIndexList = mongoTemplate.find(query, InvertIndex.class, tableName);
            System.out.println("    文章"+url+"的索引信息查询完毕！");
            System.out.println("    正在生成结果集合。。。");
            for (String stem : stems.keySet()) {
                if ("ARTICLE_ID".equals(stem)) {
                    page.setId((String) stems.get(stem));
                    stems.remove(stem);
                } else {
                    InvertIndex indexSet = null;
                    for (InvertIndex index : invertIndexList) {
                        if (index.getTokenId().equals(stem)) {
                            indexSet = index;
                        }
                    }
//                InvertIndex indexSet = mongoTemplate.findById(stem, InvertIndex.class, tableName);
                    if (indexSet==null) {
                        indexSet = new InvertIndex(stem, new HashMap<>());
                    }
                    Index i = new Index(url, stems.get(stem,String.class));
                    indexSet.getIndexMap().put(url.replace('.','$'), i);
                    indexDFRes.add(new IndexDF(stem, indexSet.getIndexMap().size()));
                    invertIndexRes.add(indexSet);
                }
            }
            System.out.println("    结果集合生成完毕");
            if (invertIndexRes.size()!=0) {
                System.out.println("    生成索引批量查询作业。。。");
                BulkOperations indexBulkOps = mongoTemplate.bulkOps(BulkOperations.BulkMode.ORDERED, InvertIndex.class, tableName);
                invertIndexRes.forEach(document -> {
                    Query index_bulk_query = new Query(Criteria.where("_id").is(document.getTokenId()));
                    Update update = new Update().set("_id", document.getTokenId()).set("indexMap", document.getIndexMap());
                    indexBulkOps.upsert(index_bulk_query, update);
                });
                System.out.println("    插入数据中。。。");
                indexBulkOps.execute();
                System.out.println("    插入完毕！");
            }

            if (indexDFRes.size()!=0) {
                System.out.println("    生成df批量查询作业。。。");
                BulkOperations dFbulkOps = mongoTemplate.bulkOps(BulkOperations.BulkMode.ORDERED, IndexDF.class, "stem_df");
                indexDFRes.forEach(document -> {
                    Query df_bulk_query = new Query(Criteria.where("_id").is(document.getTokenId()));
                    Update update = new Update().set("_id", document.getTokenId()).set("df", document.getDf());
                    dFbulkOps.upsert(df_bulk_query, update);
                });
                System.out.println("    插入数据中。。。");
                dFbulkOps.execute();
                System.out.println("    插入完毕！");
            }

            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }

    }

    private JSONObject extractContentIndex(String origin_content,String url) {
        System.out.println("    正在提取文章"+url+"的关键字。。。");
        JSONArray jsonArray = new JSONArray();
        jsonArray.addAll(Arrays.asList(indexUtil.pretreatmentString(origin_content)));

        String param = jsonArray.toString().replace('"', '\'');
        String requestBody = "{\"content\":\""+param+"\"}";
        JSONObject stems = PythonServiceApi.getPyServiceRes(requestBody, "http://localhost:8888/disordered_tokenize");
        System.out.println("    文章"+url+"的关键字提取完毕！");
        System.out.println("    正在查询文章"+url+"的索引信息。。。");

        return stems;
    }

    private JSONObject extractTitleIndex(String origin_content, String url) {

        String mergedString = String.join(" ", indexUtil.pretreatmentString(origin_content));
        if (mergedString.length()>8000) {
            mergedString = mergedString.substring(0,8000);
        }
        String requestBody = "{\"content\":\""+mergedString+"\"}";
        JSONObject stems = PythonServiceApi.getPyServiceRes(requestBody,"http://localhost:8888/ordered_tokenize");
        JSONArray token_ids = (JSONArray) stems.get("TOKEN_ID");
        if (token_ids==null) {
            throw new RuntimeException("标题为空！");
        }
        String[] originStrings = new String[token_ids.size()];
        for (int i=0;i< token_ids.size();i++) {
            originStrings[i]=token_ids.get(i).toString();
        }
        JSONObject res = searchUtil.extractPhrase(originStrings);

        return res;
    }

    private void updatePhrases() {
        String regex = ".*-.*"; // 正则表达式，匹配包含 - 的字符串

        Criteria criteria = Criteria.where("_id").regex(regex);
        Query query = new Query(criteria);

        List<InvertIndex> result0 = mongoTemplate.find(query, InvertIndex.class, "title_index");
        List<InvertIndex> result1 = mongoTemplate.find(query, InvertIndex.class, "content_index");
        List<String> phrase = new ArrayList<>();
        for (InvertIndex i : result0) {
            phrase.add(i.getTokenId());
            mongoTemplate.save(new IndexDF(i.getTokenId(), i.getIndexMap().size()),"phrases");
        }

        for (InvertIndex i : result1) {
            phrase.add(i.getTokenId());
            mongoTemplate.save(new IndexDF(i.getTokenId(), i.getIndexMap().size()),"phrases");
        }
    }

    private void DBInit() {
        if (!mongoTemplate.collectionExists("forward_index")) {
            mongoTemplate.createCollection("forward_index");
        }
        if (!mongoTemplate.collectionExists("title_index")) {
            mongoTemplate.createCollection("title_index");
        }
        if (!mongoTemplate.collectionExists("content_index")) {
            mongoTemplate.createCollection("content_index");
        }
        if (!mongoTemplate.collectionExists("stem_df")) {
            mongoTemplate.createCollection("stem_df");
        }
        if (!mongoTemplate.collectionExists("phrases")) {
            mongoTemplate.createCollection("phrases");
        }
        if (!mongoTemplate.collectionExists("pageLink")) {
            mongoTemplate.createCollection("pageLink");
        }
    }

    private void updateParent() {
        Query query = new Query();
        List<Page> pages = mongoTemplate.find(query,Page.class,"forward_index");
        for (Page page : pages) {
            Set<String> urlSet = page.getChildrenLink();
            for (String url:urlSet) {
                for (Page childPage : pages) {
                    if (childPage.getUrl().equals(url)) {
                        Set<String> newParentSet = childPage.getParentLink();
                        newParentSet.add(url);
                        childPage.setParentLink(newParentSet);
                        break;
                    }
                }
            }
        }
        for (Page page : pages) {
            mongoTemplate.save(page,"forward_index");
        }
    }
}
