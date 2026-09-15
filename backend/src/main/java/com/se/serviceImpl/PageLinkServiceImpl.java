package com.se.serviceImpl;

import com.se.entity.Page;

import java.util.Map;

public interface PageLinkServiceImpl {
    void parsePageLink(String startUrl, int max_url, int max_depth);
}
