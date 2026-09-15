package com.se.entity;
import lombok.AllArgsConstructor;
import lombok.Data;

import java.util.Date;
import java.util.List;
import java.util.Set;

@Data
@AllArgsConstructor
public class SearchResult {
    String url;
    String title;
    Float score;
    String content;
    Date lastModification;
    Float pageSize;
    String logoSVG;
    String img;
    Set<String> parentLinks;
    Set<String> childLinks;
    Set<IndexDF> keywordsFrequency;     // should look like {keyword: <String>, count: <Integer>)

    public SearchResult(String url, String title, Float score, String content, Set<String> parentLinks, Set<String> childLinks,Set<IndexDF> keywordsFrequency, String logoSVG, String img) {
        this.url = url;
        this.title = title;
        this.score = score;
        this.content = content;
        this.parentLinks = parentLinks;
        this.childLinks = childLinks;
        this.keywordsFrequency = keywordsFrequency;
        this.logoSVG = logoSVG;
        this.img = img;
    }
}
