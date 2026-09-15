package com.se.dto;

import cn.hutool.json.JSONObject;
import lombok.AllArgsConstructor;
import lombok.Data;

@AllArgsConstructor
@Data
public class WebSocketDto {
    int type; // 0:related res, 1:AI conclusion
    JSONObject msg;
}
