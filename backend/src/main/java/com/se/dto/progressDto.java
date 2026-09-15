package com.se.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@AllArgsConstructor
@Data
public class progressDto {
    int taskNum;
    int finishNum;
    String startUrl;
}
