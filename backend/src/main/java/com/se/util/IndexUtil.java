package com.se.util;

import org.springframework.stereotype.Component;

@Component
public class IndexUtil {
    public String[] pretreatmentString(String originalDoc) {
        originalDoc = originalDoc.toLowerCase();
        String[] result = originalDoc.split("[^\\p{L}\\p{N}\\s]+");

        return result;
    }
}
