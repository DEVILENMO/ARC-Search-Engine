package com.se.api;

import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
public class PythonServiceApi {
    public static JSONObject getPyServiceRes(String requestBody, String url) {
        JSONObject res = new JSONObject();
        try {
            RestTemplate restTemplate = new RestTemplate();

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<String> requestEntity = new HttpEntity<>(requestBody, headers);

            ResponseEntity<String> response = restTemplate.postForEntity(url, requestEntity, String.class);

            String responseBody = response.getBody();
            System.out.println(responseBody);

            res = JSONUtil.parseObj(responseBody);
        } catch (Exception e) {
            e.printStackTrace();
        }

        return res;
    }
}
