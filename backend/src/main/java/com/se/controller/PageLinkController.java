package com.se.controller;

import com.se.entity.*;
import com.se.service.PageLinkService;
import com.se.util.IndexUtil;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;


import java.io.IOException;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@RestController
@RequestMapping("/PageLink")
public class PageLinkController {
    @Autowired
    IndexUtil indexUtil;
    @Autowired
    PageLinkService pageLinkService;
    @Autowired
    MongoTemplate mongoTemplate;
    private ExecutorService executor = Executors.newFixedThreadPool(10);
    @RequestMapping("/Parse")
    public int parsePageLink(@RequestBody String startUrlList){
        startUrlList=startUrlList.substring(1,startUrlList.length()-1);
        String[] urlStrings = startUrlList.split(",");

        for (String startUrl : urlStrings) {
            String[] url_num = startUrl.split(" ");
            int max_url = 50;
            if (url_num.length==2) {
                max_url = Integer.parseInt(url_num[1]);
            }
            String url = url_num[0];
            int finalMax_url = max_url;
            executor.submit(() -> {
                pageLinkService.parsePageLink(url, finalMax_url, 3);
            });
        }
        return 0;
    }
}
