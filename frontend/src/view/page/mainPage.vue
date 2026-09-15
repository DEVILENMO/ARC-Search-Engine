<template>
    <div class="main">
        <div class="card">
            <el-image :src="log_url" class="logo" fit="cover"></el-image>
            <p class="title">ARC Search Engine</p>
            <p class="desc">A next-generation AI search engine supporting any UTF-8 compatible language.</p>

            <el-form ref="ruleForm" :model="ruleForm" :rules="rules" class="demo-ruleForm" label-width="100px" status-icon @submit.native.prevent>
                <el-form-item prop="content">
                    <el-input v-model="ruleForm.content" autocomplete="false" type="text" style="width:60%" @keyup.enter.native="submitForm('ruleForm')" clearable>
                        <i slot="prefix" class="el-input__icon el-icon-search"></i>
                    </el-input>
                    <el-button round @click.native="drawer = true" icon="el-icon-s-tools" style="position: fixed;right: 1%;top: 1%;"></el-button>
                </el-form-item>
            </el-form>
            <el-drawer
                :visible.sync="drawer"
                direction="rtl">
                    <el-input v-model="start_url" autocomplete="false" type="text" style="width:60%;margin:2%;display:inline-block" clearable>
                    </el-input>
                    <br>
                    <el-button type="primary" @click.native="parseUrl()" style="margin:2%;display:inline-block" >submit</el-button>
                    <br>
                    <!-- <span style="margin:2%" >Please enter the crawler command in the following format:</span>
                    <br> -->
                    <!-- <span style="margin:2%" >url1 number1,url2 number2,...</span> -->
                    <div class="progress" v-for="(val, key) in progressMap" :key='key'>
                        {{val[0]}}
                        <el-progress :percentage="parseInt(val[1])"></el-progress>
                    </div>
            </el-drawer>
        </div>

        <p class="footer"> Copyright @HKUST-LAM-LIU-WANG Reserved</p>
    </div>
</template>
<script>
/* eslint-disable */
export default {
    name: "Login",
    components: {},
    data() {
        return {
            drawer: false,
            isVisible: false,
            log_url: require("@/assets/logo.png"),
            ruleForm: {
                content: '',
            },
            start_url: "",
            rules: {
                content: [
                    {required: true, message: 'no content', trigger: 'blur'}
                ]
            },
            history_res: [],
            webSocket: null,
            progressMap: new Map(),
        };
    },
    mounted() {
        if (localStorage.getItem('history') && JSON.parse(localStorage.getItem('history'))) {
            this.history_res = JSON.parse(localStorage.getItem('history'))
        }
        this.connect()
    },
    methods: {
        parseUrl() {
            this.$http.post("/PageLink/Parse", {urls: this.start_url})
            this.$message.success("Your crawler request is being processed, please check the backend console for details")
            let url_list = this.start_url.split(",")
            url_list && url_list.forEach(item => {
                this.progressMap.set(item.split(" ")[0], 0)
            })

            this.$forceUpdate()
        },
        submitForm(formName) {
            this.$refs[formName].validate((valid) => {
                if (valid) {
                    var words = this.ruleForm.content
                    this.$http.post("/search/get", {keywords: words}).then(res => {
                        this.$router.push({path: '/res', query: {data: res.data.results, related: res.data.relatedResList, keywords: words}})
                        let val = words.trim()
                        if (this.history_res.indexOf(val) === -1) {
                            // 添加到头部，最多保留10个
                            this.history_res.unshift(val)
                            this.history_res = this.history_res.slice(0, 10)
                            localStorage.setItem('history', JSON.stringify(this.history_res))
                        }
                    }).catch(e => {
                        console.log(e)
                        this.$message.error("系统异常")
                    })
                } else {
                    console.log('error submit!!');
                    return false;
                }
            });
        },
        connect() {
            // 创建WebSocket连接
            const url = this.GLOBAL_WS_URL
            this.webSocket = new WebSocket(url)
            // 监听WebSocket事件
            this.webSocket.onopen = () => {
                console.log('WebSocket连接已打开')
            };

            this.webSocket.onmessage = (event) => {
                if (event) {
                    let res = JSON.parse(event.data)
                    if (res.type == 2 && res.msg) {
                        let progress = (res.msg.finishNum / res.msg.taskNum * 100).toFixed(2)
                        if (parseInt(progress) > 100) {
                            progress = 100
                        }
                        this.progressMap.set(res.msg.startUrl, progress)
                        this.$forceUpdate()
                    }
                }
            };

            this.webSocket.onclose = () => {
                console.log('WebSocket连接已关闭，3s后重连')
                setTimeout(() => this.connect(), 3000)
            };
        }
    }
}
</script>

<style scoped>
/*主界面*/
.main {
    width: 100%;
    height: 100%;
    /* background-image: url("../assets/img/wallhaven-zygeko.jpg"); */
    position: absolute;
    left: 0;
    top: 0;
    background-size: 100% 100%;
}

/*el-card样式*/
.card {
    position: absolute;
    left: 0;
    right: 0;
    top: 30%;
    margin: auto;
    width: 80%;
    min-width: 300px;
    height: 50%;
    text-align: center;
}

/*login*/
.logo {
    width: 100px;
    height: 100px;
    margin-top: 0px;
}

.title {
    font-family: 'Agency FB', serif;
    font-size: 30px;
    font-weight: bold;
    margin: 0;
    margin-bottom: 5px;
}

.desc {
    letter-spacing: 2px;
    color: #999a99;
    font-family: 'Agency FB', serif;
    font-size: 15px;
    margin: 0;
    margin-bottom: 10px;
}

.footer {
    z-index: 9999;
    position: fixed;
    bottom: 0;
    width: 100%;
    text-align: center;
}

.demo-ruleForm {
    margin-left: -20px;
    margin-right: 60px;
}
.progress {
    text-align: left;
    margin: 2%;
    margin-left: 10%;
}
</style>