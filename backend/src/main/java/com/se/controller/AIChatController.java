package com.se.controller;

import com.se.dto.AIChatDto;
import com.se.service.AIChatService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/AIChat")
public class AIChatController {
    @Autowired
    AIChatService aiChatService;

    @RequestMapping("/getReply")
    public String getReply(@RequestBody AIChatDto aiChatDto) {
        return aiChatService.getReply(aiChatDto);
    }
}
