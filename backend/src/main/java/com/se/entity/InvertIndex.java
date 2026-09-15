package com.se.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import org.springframework.data.annotation.Id;

import java.util.List;
import java.util.Map;

@Data
@AllArgsConstructor
public class InvertIndex {
    @Id
    String tokenId;
    Map<String,Index> indexMap;
}
