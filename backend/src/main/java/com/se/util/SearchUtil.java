package com.se.util;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONUtil;
import com.se.entity.IndexDF;
import com.se.entity.InvertIndex;
import com.se.entity.Page;
import org.python.antlr.op.In;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import cn.hutool.json.JSONObject;
import org.springframework.web.client.RestTemplate;
import org.yaml.snakeyaml.events.Event;

@Component
public class SearchUtil {
    @Autowired
    MongoTemplate mongoTemplate;

    // given Q and D(containing both title and content documents) with their tfidf weights to compute consine similarity
    public float computeCosineSimilarity(Map<String, Float> queryTerms, Map<String, Float> docTerms){
        float dotProduct = 0.0F;
        float queryMagnitude = 0.0F;
        float documentMagnitude = 0.0F;

        // query magnitude
        for (Map.Entry<String, Float> queryTerm : queryTerms.entrySet()) {
            String term = queryTerm.getKey();
            float queryTermFrequency = queryTerm.getValue();
//            Set<String> phrasesSet = getSimilarPhrases(docTerms.keySet(),term);
            float documentTermFrequency = docTerms.getOrDefault(term, 0.0F);

            dotProduct += queryTermFrequency * documentTermFrequency;
            queryMagnitude += Math.pow(queryTermFrequency, 2);
        }

        // document magnitude
        for (float documentTermFrequency : docTerms.values()) {
            documentMagnitude += Math.pow(documentTermFrequency, 2);
        }

        queryMagnitude = (float) Math.sqrt(queryMagnitude);
        documentMagnitude = (float) Math.sqrt(documentMagnitude);

        if (queryMagnitude == 0 || documentMagnitude == 0) {
            return 0.0F; // Handle division by zero
        }

        return dotProduct / (queryMagnitude * documentMagnitude);

    }

    // for tf frequency object {<key> : <tf value>}
    public Map<String, Integer> jsonToHashMap(JSONObject jsonObject) {
        Map<String, Integer> result = new HashMap<>();

        for (String key : jsonObject.keySet()) {
            if (!"ARTICLE_ID".equals(key)) {
                result.put(key, (Integer) jsonObject.get(key));
            }
        }
        return result;
    }

    // to find max tf values for normalization of tf
    public int findMaxValue(JSONObject jsonObject){
        int maxValue = 0;
        for (String key : jsonObject.keySet()) {
            if (!"ARTICLE_ID".equals(key)) {
                int value = jsonObject.getInt(key);

                if (value > maxValue) {
                    maxValue = value;
                }
            }
        }

        return maxValue;
    }

    // compute tfidf for either title documents or content documents
    public Map<String, Map<String, Float>> computeDocTfIdf(List<String> allDocs, String columnKey, Integer N, Integer boostFactor,List<IndexDF> results){
        Map<String, Map<String, Float>> docsTerms = new HashMap<>();
        Map<String, Integer> dfMap = new HashMap<>();
        for (IndexDF df : results) {
            dfMap.put(df.getTokenId(),df.getDf());
        }

        Query pageQuery=new Query();
        pageQuery.addCriteria(Criteria.where("url").in(allDocs));
        List<Page> docPages = mongoTemplate.find(pageQuery, Page.class,"forward_index");
        for (Page docPage : docPages) {
            // compute tf, tf_max
//            String docResult = jdbmUtil.searchEntry("forward_index", doc);
//            Query docQuery=new Query();
//            docQuery.addCriteria(Criteria.where("url").is(doc));
//            Page docPage = mongoTemplate.findOne(docQuery, Page.class, "forward_index");
            if (docPage.getUrl()==null) {
                continue;
            }
            JSONObject docJSON = new JSONObject(docPage);
            JSONObject docTfJSON = new JSONObject((docJSON.getObj(columnKey)));
            if (docTfJSON.size()<=1) {
                continue;
            }
            int docTfMax = findMaxValue(docTfJSON);// tf_max: the most frequent term in doc i (by calling forward index table)
            Map<String, Integer> docTfs = jsonToHashMap(docTfJSON);     // Tf of all terms inside a doc
            Map<String, Float> docTerms = new HashMap<>();              // Tfidf of all terms inside a doc

            // compute df for each term in doc
            for(String key : docTfs.keySet()){
                int docDf = 0;
                int docTf = docTfs.get(key);
                if (!dfMap.isEmpty() && dfMap.containsKey(key)) {
                    docDf+=dfMap.get(key);
                }

                // compute idf, TfIdf
                if (docDf!=0) {
                    float docIdf = (float) (Math.log(N/(float) docDf)/Math.log(2));
                    float docTfIdf = docTf * docIdf / docTfMax;
                    docTfIdf *= boostFactor;
                    if (key.contains("-")) {
                        int boostNum = (int) key.chars()
                                .filter(ch -> ch == '-')
                                .count();
                        docTfIdf *= (2 * boostNum); // boost phrases
                    }
                    docTerms.put(key, docTfIdf);
                }
            }
            docsTerms.put(docPage.getUrl(), docTerms);
        }
        return docsTerms;
    }

    // sort descendingly and get top X results
    public List<Map.Entry<String, Float>> getTopResults(Map<String, Float> hashMap, Integer limit){
        List<Map.Entry<String, Float>> entryList = new ArrayList<>(hashMap.entrySet());

        // Sort the List in descending order based on values
        entryList.sort(Map.Entry.<String, Float>comparingByValue().reversed());

        if (entryList.size() > limit) {
            entryList = entryList.subList(0, limit);
        }

        return entryList;
    }

    // merge tfidf of title and content tables
    public Map<String, Map<String, Float>> mergeDocsWeightings(Map<String, Map<String, Float>> docs1, Map<String, Map<String, Float>> docs2){
        Map<String, Map<String, Float>> docsTerms = new HashMap<>();

        for (Map.Entry<String, Map<String, Float>> doc : docs1.entrySet()) {
            String key = doc.getKey();
            Map<String, Float> weights = doc.getValue();
            docsTerms.put(key, weights);
        }

        for (Map.Entry<String, Map<String, Float>> entry : docs2.entrySet()) {
            String key = entry.getKey();
            Map<String, Float> weights = entry.getValue();
            if(docsTerms.containsKey(key)){
                for(Map.Entry<String, Float> innerEntry : weights.entrySet()){
                    String innerKey = innerEntry.getKey();
                    float innerValue = innerEntry.getValue();      // weights for content doc
                    if(docsTerms.get(key).containsKey(innerKey)){
                        float mergedWeight = docsTerms.get(key).get(innerKey) + innerValue;
                        docsTerms.get(key).put(innerKey, mergedWeight);     // merge 2 weights together
                    } else{
                        docsTerms.get(key).put(innerKey, innerValue);
                    }
                }
            } else {
                docsTerms.put(key, weights);
            }
        }
        return docsTerms;

    }

    public JSONObject extractPhrase(String[] originStems) {
        Query query = new Query();

        List<IndexDF> phrasesList = mongoTemplate.find(query, IndexDF.class, "phrases");
        Set<String> phrasesSet = new HashSet<>();
        for (IndexDF i : phrasesList) {
            phrasesSet.add(i.getTokenId());
        }
        JSONObject res = new JSONObject();
        if (originStems.length<=1) {
            for (String originStem : originStems) {
                res.set(originStem, 1);
            }
            return res;
        }
        for (int i=0;i<originStems.length;i++) {
            for (int j=1;j<originStems.length;j++) {
                StringBuilder key = new StringBuilder();
                for (int k=i;k<=j;k++) {
                    key.append(originStems[k]).append("-");
                }
                if (j-i>=1) {
                    String phraseIndex = key.substring(0,key.length()-1);
                    if (phrasesSet.contains(phraseIndex)) {
                        res.set(phraseIndex,1);
                    }
                }
            }
            res.set(originStems[i],1);
        }

        JSONObject resTemp = new JSONObject();
        for (String key : res.keySet()) {
            int count = 0;
            for (String keyT : res.keySet()) {
                count++;
                if (!key.equals(keyT)&&keyT.contains(key)) {
                    break;
                }
            }
            if (count==res.keySet().size()) {
                resTemp.set(key,1);
            }
            if (key.contains("-")) {
                resTemp.set(key,1);
            }
        }

        JSONObject phraseRes = new JSONObject();
        for (String JSONKey : resTemp.keySet()) {
            phraseRes.set(JSONKey,1);
            for (IndexDF i : phrasesList) {
                String phrase = i.getTokenId();
                int subStringLen = longestCommonSubstring(phrase, JSONKey);
                if ((float)subStringLen/JSONKey.length()>0.95 && Math.abs(JSONKey.length()-phrase.length())<(float)JSONKey.length()*0.2) {
                    phraseRes.set(phrase,1);
                }
            }
        }
        return phraseRes;
    }
    private int longestCommonSubstring(String str1,String str2) {
        int m = str1.length();
        int n = str2.length();
        int[][] dp = new int[m + 1][n + 1];
        int maxLength = 0;  // 最长公共子串的长度

        // 使用动态规划填充dp数组
        for (int i = 1; i <= m; i++) {
            for (int j = 1; j <= n; j++) {
                if (str1.charAt(i - 1) == str2.charAt(j - 1)) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                    maxLength = Math.max(maxLength, dp[i][j]);
                } else {
                    dp[i][j] = 0;
                }
            }
        }

        return maxLength;
    }
}
