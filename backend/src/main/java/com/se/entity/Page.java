package com.se.entity;

import cn.hutool.json.JSONObject;
import lombok.AllArgsConstructor;
import lombok.Data;
import org.springframework.data.annotation.Id;

import java.util.List;
import java.util.Set;

@Data
@AllArgsConstructor
public class Page {
    @Id
    String id;
    String url;
    String title;
    String content;
    JSONObject title_tf;
    JSONObject content_tf;
    String img;
    String icon;
    Set<String> childrenLink;
    Set<String> parentLink;

    public Page(String id, String url, String title, String content, String img, String icon,Set<String> childrenLink, Set<String> parentLink) {
        this.id = id;
        this.url = url;
        this.title = title;
        this.content = content;
        this.img = img;
        this.icon = icon;
        this.childrenLink = childrenLink;
        this.parentLink = parentLink;
    }

    public Page() {
    }
}
