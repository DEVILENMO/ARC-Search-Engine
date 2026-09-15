package com.se.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import org.springframework.data.annotation.Id;

@AllArgsConstructor
@Data
public class IndexDF {
    @Id
    String tokenId;
    int df;
}
