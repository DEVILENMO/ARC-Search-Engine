package com.se.dto;

import com.se.entity.IndexDF;
import com.se.entity.RelatedRes;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

import com.se.entity.SearchResult;

@Data
public class SearchResDto {

    List<SearchResult> results;

    Set<String> keywordsTokenId;

    public SearchResDto() {
        results = new ArrayList<>();
    }

    public void addResults(String url, String title, Float score, String content, Set<String> parentLinks, Set<String> childrenLinks, Set<IndexDF> keyWordsFrequency, String logoSVG, String img){
        SearchResult newResult = new SearchResult(url, title, score, content, parentLinks,childrenLinks,keyWordsFrequency,logoSVG,img);
        results.add(newResult);
    }
}

