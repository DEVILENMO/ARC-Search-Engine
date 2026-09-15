<template>
    <div>
        <div class="profile_picture">
        </div>
        <div class="type">
            {{chatBubble.type}}:
        </div>
        <div class="bubble">
            {{chatBubble.content}}
        </div>
    </div>
</template>

<script>
export default{
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
        chatBubble:{
            type: Object,
            default: null,
            required: false,
        }
    },
}
</script>

<style scoped>
.type {
    display: inline-block;
    width: 10%;
    vertical-align: top;
}
.bubble {
    display: inline-block;
    width: 80%;
    vertical-align: top;
}
</style>
