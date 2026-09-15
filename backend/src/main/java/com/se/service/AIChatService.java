package com.se.service;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.se.api.PythonServiceApi;
import com.se.dto.AIChatDto;
import com.se.dto.WebSocketDto;
import com.se.entity.Message;
import com.se.serviceImpl.AIChatServiceImpl;
import com.se.util.RedisUtil;
import com.se.util.WebSocketServer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

@Service
public class AIChatService implements AIChatServiceImpl {
    @Autowired
    RedisUtil redisUtil;
    @Override
    public String getReply(AIChatDto aiChatDto) {
        List<Message> topList = new ArrayList<>();
        String sessionId = "chat_"+aiChatDto.getSessionId();
        // 查看缓存里是否有对应sessionID的记忆，如果有就直接读取作为新的输入
        if (redisUtil.exists(sessionId)){
            String chatMemory = (String) redisUtil.get(sessionId);
            JSONArray memoryArr = JSONUtil.parseArray(chatMemory);
            for (int i = 0; i< memoryArr.size();i++) {
                JSONObject memory = memoryArr.getJSONObject(i);
                topList.add(new Message(memory.getStr("role"),memory.getStr("content")));
            }
        }
        String res = "";
        topList.add(new Message("user", aiChatDto.getUserQuery()));

        String origin = JSONUtil.parseArray(topList).toString();
        JSONObject AIReply = PythonServiceApi.getPyServiceRes(origin,"http://localhost:8888/chat_with_AI");
        res = (String) AIReply.get("content");
        // 记录新的AI回复，更新记忆
        topList.add(new Message("assistant", res));
        redisUtil.set(sessionId,JSONUtil.toJsonStr(topList));
        return res;
    }
}
