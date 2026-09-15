<template>
    <div class="main">
        <el-row style="display: flex;align-items: center;">
            <el-col :span="2">
                <div>
                    <el-image :src="log_url" class="inner_logo" fit="cover"></el-image>
                </div>
            </el-col>
            <el-col :span="8">
                <!-- 历史记录弹窗 -->
                <el-popover
                    placement="bottom"
                    width="600"
                    title="HISTORY SEARCH"
                    trigger="focus">
                    <div>
                        <div v-for="keyword in history_res" :key="keyword" style="margin:1%">
                        <el-link type="info" @click="sendSearchRequest(keyword)">{{keyword}}</el-link>
                        </div>
                        <div style="text-align: right; margin-top: 10px;">
                        <el-button icon="el-icon-delete" circle @click.native="del()"></el-button>
                        </div>
                    </div>
                    <el-input slot="reference" v-model="ruleForm.content" autocomplete="off" type="text" @keyup.enter.native="sendSearchRequest(ruleForm.content)" clearable>
                        <i slot="prefix" class="el-input__icon el-icon-search"></i>
                    </el-input>
                </el-popover>
                <!-- <div>
                    <el-input v-model="ruleForm.content" autocomplete="off" type="text" @keyup.enter.native="handleEnter(ruleForm.content)" clearable> 
                        <i slot="prefix" class="el-input__icon el-icon-search"></i>
                    </el-input>
                </div> -->
            </el-col>
        </el-row>
        <el-row>
            <el-col :span="12" :offset="2" v-loading="page_loading">
                <div class="res" ref="scrollContainer">
                    <!-- 搜索结果列表 -->
                    <link-card v-for="item in tableData.slice((currentPage-1)*pageSize,currentPage*pageSize)"
                        :key="item.url"
                        :searchResult="item">
                    </link-card>
                    <!-- 相关搜索列表 -->
                    <div v-loading="related_loading">
                        <el-table
                            :data="related"
                            @row-click="handleRowClick"
                            style="width: 100%">
                            <el-table-column
                                prop="words"
                                label="related search">
                                <template slot-scope="scope">
                                    <i class="el-icon-search"></i>
                                    <div style="display: inline-block;margin-left: 10px;">{{ scope.row.words }}</div>
                                </template>
                            </el-table-column>
                        </el-table>
                    </div>
                    <p class="footer"> Copyright @HKUST-LAM-LIU-WANG Reserved</p>
                </div>
            </el-col>
            <el-col :span="6" :offset="2">
                <div class="extend_function">
                    <div class="function_title">
                        AI SUMMARY
                    </div>
                    <!-- AI总结，聊天 -->
                    <div class="ai_function" v-loading="summary_loading">
                        <chat-bubble v-for="item in chatHistory" 
                            :key="item"
                            :chatBubble="item">
                        </chat-bubble>
                    </div>
                    <div class="related_function">
                        <el-input
                            type="textarea"
                            :rows="2"
                            placeholder="请输入内容"
                            v-model="AIQuery"
                            @keyup.enter.native="sendAIChatRequest(AIQuery)">
                        </el-input>
                        <!-- <div class="tag" v-for="i in related" :key=i.tokenId>
                            <el-tag type="info" @click="handleEnter(i.words)">{{i.words}}</el-tag>
                        </div> -->
                    </div>
                </div>
            </el-col>
        </el-row>
        <el-row>
            <el-col :span="8">
                <el-pagination
                :current-page.sync="currentPage"
                :page-size="pageSize"
                layout="total, prev, pager, next"
                :total="total"
                @current-change="handleCurrentChange">
                </el-pagination>
            </el-col>
        </el-row>
    </div>
</template>

<script>
/* eslint-disable */
import LinkCard from '@/components/LinkCard.vue'
import ChatBubble from '@/components/ChatBubble.vue'
export default {
    name: "res",
    components : {
        LinkCard,
        ChatBubble
    },
    data() {
        var validateUser = (rule, value, callback) => {
            if (value === '') {
                callback(new Error('no content'));
            } else {
                if (this.ruleForm.password !== '') {
                    this.$refs.ruleForm.validateField('password');
                }
                callback();
            }
        };
        return {
            total: 0,
            keywords: "",
            conclusion: "",
            currentPage: 1,
            pageSize: 10,
            log_url: require("@/assets/logo_complete_version.png"),
            ruleForm: {
                content: '',
                client_id: 'app',
                client_secret: 'app',
            },
            rules: {
                pass: [
                    {validator: validateUser, trigger: 'blur'}
                ]
            },
            tableData: [],
            related:[],
            wsUrl: 'ws://127.0.0.1:8899/websocket',
            webSocket: null,
            related_loading: true,
            summary_loading: true,
            page_loading: true,
            history_res:[],
            AIQuery: '',
            chatHistory: []
        };
    },
    created() {
    },
    mounted() {
        this.tableData = this.$route.query.data
        this.ruleForm.content = this.$route.query.keywords
        this.total = this.tableData.length
        this.currentPage = 1
        this.page_loading = false
        this.connect ()

        if (localStorage.getItem('history')&&JSON.parse(localStorage.getItem('history'))) {
			this.history_res = JSON.parse(localStorage.getItem('history'))
		}
    },
    methods: {
        del() {
			localStorage.removeItem('history')
			this.history_res = []
		},
        /**
         * 翻页事件
         * **/
        handleCurrentChange(val) {
            this.currentPage = val
            this.$refs.scrollContainer.scrollTop = 0
        },
        /**
         * 列表点击事件
        */
        handleRowClick(row) {
            this.related_loading=true
            this.summary_loading=true
            this.page_loading=true
            var _this = this
            this.$http.post("/search/get", row.words).then(res => {
                _this.keywords = row.words
                _this.tableData=res.data.results
                _this.total = _this.tableData.length
                _this.currentPage = 1
                _this.$refs.scrollContainer.scrollTop = 0
                _this.page_loading = false
                if (localStorage.getItem('history')&&JSON.parse(localStorage.getItem('history'))) {
                    this.history_res = JSON.parse(localStorage.getItem('history'))
                }
                let val = row.words.trim()
                if (!val) { //判断输入的值是否为空
                    return
                }
                if (this.history_res.indexOf(val) === -1) {
                    // 添加到头部
                    this.history_res.unshift(val)
                    // 最多显示10个
                    this.history_res.slice(0, 2)
                    localStorage.setItem('history', JSON.stringify(this.history_res))
                }
            }).catch(e => {
                _this.$message.error("系统异常")
            })
        },
        /**
         * 回车搜索
        */
        sendSearchRequest(words) {
            this.related_loading=true
            this.summary_loading=true
            this.page_loading=true
            var _this = this
            this.$http.post("/search/get", words).then(res => {
                _this.keywords = words
                _this.tableData=res.data.results
                _this.total = _this.tableData.length
                _this.currentPage = 1
                _this.$refs.scrollContainer.scrollTop = 0
                _this.page_loading = false
                if (localStorage.getItem('history')&&JSON.parse(localStorage.getItem('history'))) {
                    this.history_res = JSON.parse(localStorage.getItem('history'))
                }
                let val = words.trim()
                if (!val) { //判断输入的值是否为空
                    return
                }
                if (this.history_res.indexOf(val) === -1) {
                    // 添加到头部
                    this.history_res.unshift(val)
                    // 最多显示10个
                    this.history_res.slice(0, 2)
                    localStorage.setItem('history', JSON.stringify(this.history_res))
                }
            }).catch(e => {
                _this.$message.error("系统异常")
            })
        },
        sendAIChatRequest (userQuery) {
            // 更新用户输入的文字到AI聊天界面
            this.chatHistory.push({
                type: "user",
                content: userQuery
            })
            this.AIQuery = ''
            if (!localStorage.getItem('session_id')) {
                localStorage.setItem('session_id', this.generateSessionId())
            }
            let sessionId = localStorage.getItem('session_id')
            let param = {
                sessionId: sessionId,
                userQuery: userQuery
            }
            this.$http.post("/AIChat/getReply", param).then(res => {
                let chatMsg = {
                    type: "ai",
                    content: res.data
                }
                this.chatHistory.push(chatMsg)
            })
        },
        /**
         * 创建WebSocket链接
        */
        connect () {
            // 创建WebSocket连接
            const url = this.wsUrl
            this.webSocket = new WebSocket(url)
            // 监听WebSocket事件
            this.webSocket.onopen = () => {
                console.log('WebSocket连接已打开')
            };

            this.webSocket.onmessage = (event) => {
                if (event) {
                    console.log("websocket msg："+event.data)
                    let res = JSON.parse(event.data)
                    
                    if (res.type == 0) {
                        this.related = []
                        res.msg&&Object.keys(res.msg).forEach(key => {
                            const value = res[key];
                            let words = {
                                tokenId: value,
                                words: key
                            }
                            this.related.push(words);
                        });
                        this.related_loading=false
                    } else if (res.type == 1) {
                        let chatMsg = {
                            type: "ai",
                            content: res.msg.msg
                        }
                        this.chatHistory.push(chatMsg)
                        this.summary_loading=false
                    }
                }
            };

            this.webSocket.onclose = () => {
                console.log('WebSocket连接已关闭')
                this.connect ()
            };
        },
        // 随机生成20位的sessionID
        generateSessionId () {
            var chars = ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
            var res = ""
            for(var i = 0; i < 20 ; i ++) {
                var id = Math.ceil(Math.random()*35);
                res += chars[id];
            }
            return res;
        }
    }
}
</script>


<style>
  .res {
    height: 75vh;
    border-radius: 4px;
    overflow: auto;
    padding: 1%;
  }
  .related_function {
    height: 10vh;
    font-size: x-large;
    text-align: left;
    padding: 2%;
    overflow: auto;
  }
  .extend_function {
      border: 1px solid rgb(0, 0, 0, 0.1);
      border-radius: 10px 10px 10px 10px;
      margin-top: 5%;
  }
  .ai_function {
    height: 50vh;
    font-size: x-large;
    text-align: left;
    padding: 2%;
    overflow: auto;
    border: 1px solid rgb(0, 0, 0, 0.1);
    font-size:0.8em;
    line-height: 2;
  }
  .inner_logo {
    margin: 10%;
  }
  .tag {
    margin: 2%;
    display: inline-block;
  }
  .function_title {
      background-color: #4158D0;
      background-image: linear-gradient(43deg, #4158D0 0%, #C850C0 46%, #FFCC70 100%);
      border-radius: 10px 10px 0px 0px;
      height: 100px;
      font-size: 3em;
      font-weight: 600;
      text-align: left;
      color: white;
      display: flex;
      align-items: center; /* 垂直居中 */
      padding-left: 40px;
      font-family: math;
  }
</style>
