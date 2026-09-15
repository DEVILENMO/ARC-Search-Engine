package com.se.controller;

import com.se.dto.SearchResDto;
import com.se.service.SearchService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/search")
public class SearchController {
    @Autowired
    SearchService searchService;
    @RequestMapping("/get")
    public SearchResDto parsePageLink(@RequestBody String keywords){
        keywords=keywords.substring(1,keywords.length()-1);

        return searchService.getSearchRes(keywords);
    }
}
