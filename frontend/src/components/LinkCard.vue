<template>
    <div class="card">
        <div class="main-card">
            <div class="card-header">
                    <!-- <svg ref="SVGContainer" style="dispaly:inline-block;width: 30px;height: 30px;">
                        <path fill-rule="evenodd" clip-rule="evenodd" d="M3.73252 2.67094C3.33229 2.28484 3.33229 1.64373 3.73252 1.25764C4.11291 0.890684 4.71552 0.890684 5.09591 1.25764L7.21723 3.30403C7.27749 3.36218 7.32869 3.4261 7.37081 3.49407H10.5789C10.6211 3.4261 10.6723 3.36218 10.7325 3.30403L12.8538 1.25764C13.2342 0.890684 13.8368 0.890684 14.2172 1.25764C14.6175 1.64373 14.6175 2.28484 14.2172 2.67094L13.364 3.49407H14C16.2091 3.49407 18 5.28493 18 7.49407V12.9996C18 15.2087 16.2091 16.9996 14 16.9996H4C1.79086 16.9996 0 15.2087 0 12.9996V7.49406C0 5.28492 1.79086 3.49407 4 3.49407H4.58579L3.73252 2.67094ZM4 5.42343C2.89543 5.42343 2 6.31886 2 7.42343V13.0702C2 14.1748 2.89543 15.0702 4 15.0702H14C15.1046 15.0702 16 14.1748 16 13.0702V7.42343C16 6.31886 15.1046 5.42343 14 5.42343H4ZM5 9.31747C5 8.76519 5.44772 8.31747 6 8.31747C6.55228 8.31747 7 8.76519 7 9.31747V10.2115C7 10.7638 6.55228 11.2115 6 11.2115C5.44772 11.2115 5 10.7638 5 10.2115V9.31747ZM12 8.31747C11.4477 8.31747 11 8.76519 11 9.31747V10.2115C11 10.7638 11.4477 11.2115 12 11.2115C12.5523 11.2115 13 10.7638 13 10.2115V9.31747C13 8.76519 12.5523 8.31747 12 8.31747Z" fill="currentColor"></path>
                    </svg> -->   
                <div class="title">
                    <el-link type="primary" style="font-size: large;" :href="searchResult.url" target="_blank">{{searchResult.title ? searchResult.title : searchResult.url}} (score: {{searchResult.score.toFixed(4)}})</el-link>
                </div>            
                <div class="url">
                    <span>{{searchResult.url}}</span>
                </div> 
            </div>
            <div class="card-body">
                <div class="card-content">
                    <div>
                        {{searchResult.content}}
                    </div>
                    <!-- <div class="card-content-oneline">
                        <div>{{searchResult.lastModification ? searchResult.lastModification : (new Date()).toLocaleString()}}</div>
                        <div>{{searchResult.pageSize ? searchResult.pageSize : 0}} MB</div>
                    </div> -->
                    <el-collapse v-model="activeName" accordion>
                        <el-collapse-item title="Keywords Frequency" name="1">
                            <div>
                                <div v-for="(pair, index) in searchResult.keywordsFrequency" :key="index" style="display:inline-block;margin-right:1%">
                                    <el-tag type="info">{{pair.tokenId}}: {{pair.df}}</el-tag>
                                </div> 
                            </div>
                        </el-collapse-item>
                        <el-collapse-item title="Parent Links" name="2">
                            <div> 
                                <div v-for="(link, index) in searchResult.parentLinks" :key="index">
                                    <el-link type="primary" :href='link' target="_blank">{{link}}</el-link>
                                </div> 
                            </div>
                        </el-collapse-item>
                        <el-collapse-item title="Child Links" name="3">
                            <div> 
                                <div v-for="(link, index) in searchResult.childLinks" :key="index">
                                    <el-link type="primary" :href='link' target="_blank">{{link}}</el-link>
                                </div> 
                            </div>
                        </el-collapse-item>
                    </el-collapse>
                </div>
                <div class="card-img" v-if="searchResult.img">
                    <el-image :src="searchResult.img" class="img" fit="cover" @error="handleImageError"></el-image>
                </div>
            </div>
            
        </div>
    </div>
</template>

<script>
/* eslint-disable */
export default {
    data() {
        return {
            activeName: '',
            img_url: "https://www.baidu.com/img/flexible/logo/pc/privacy.gif",
        }
    },
    props: {
        // title:{
        //     type: String,//可以注明设置类型，
        //     default:'未定义',//默认值,
        //     required:false,//是否必须
        // },
        // url:{
        //     type: String,//可以注明设置类型，
        //     default:'未定义',//默认值,
        //     required:false,//是否必须
        // }
        searchResult:{
            type: Object,
            default: null,
            required: false,
        }
    },
    methods: {
        handleImageError (event) {
            event.target.style.display = 'none' // 隐藏图像
        }
    }
}
</script>

<style scoped>
.card {
    display: flex;
    font-family: "Poppins", sans-serif;
    transition: all 0.3s ease;
    min-height: 140px;
    margin: 20px 10px;
    font-size: medium;
    color: grey;
}
.url{
    font-size: 60%;
    color: rgb(37, 160, 37);
    word-wrap: break-word;
    display: inline-block;
}
.card-content{
    flex-direction: column;
    align-content: space-around;
    font-size: 80%;
    flex-grow: 1;
}
.card-content div{
    margin: 5px 0;
}
.card-content-oneline {
    display: flex;
    justify-content: space-between;
}
.main-card {
    flex-grow: 1;
    margin-left: 10px;
    text-align: left;
    width: 80%;
}
.title {
    margin-bottom: 5px;
    text-decoration: underline;
}
.card-header {
    text-align: left;
    margin-bottom: 10px;
}
.sterilized_status {
    height: 100%;
    width: 10%;
    float: left;
    margin-left: 5%;
    display: inline-block;
    padding-top: 20px;
}
.card:hover {
    transform: translateY(-10px);
}
.icon_container {
    display: inline-block;
    background-color: #7cdacc;
    border-radius: 100%;
    padding: 2%;
    margin: 4%;
}
.car_position {
    display: inline-block;
    vertical-align: center;
    height: 50%;
    margin: 1%;
    width: 5%;
    float: right;
    border-radius: 20%;
    background: #e0e0e0;
    box-shadow: 2px 2px 6px #bebebe,
               -2px -2px 6px #ffffff;
}
.circle{
    width: 10px;
    height: 10px;
    border-radius: 100%;
    display: inline-block;
    vertical-align: middle;
}
.card-img {
    margin: 2%;
    width:80%;
    /* display: none; */
}
.card-body {
    display: flex;
}
</style>