// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import App from './App'
import router from './router'
// 导入 ElementUI
import ElementUI from 'element-ui'
import 'element-ui/lib/theme-chalk/index.css'
import axios from 'axios'
/* eslint-disable */ 
import global from '@/css/global.css'

import websocket from 'vue-native-websocket'
Vue.use(websocket, '', {
    connectManually: true, // 手动连接
    format: 'json', // json格式
    reconnection: true, // 是否自动重连
    reconnectionAttempts: 5, // 自动重连次数
    reconnectionDelay: 2000, // 重连间隔时间
});


Vue.prototype.$http = axios

axios.defaults.baseURL = 'http://localhost:8899'
axios.defaults.timeout = 100000
axios.defaults.headers['Content-Type'] = 'application/json';
// WebSocket 地址从 baseURL 派生，保持单一配置来源
Vue.prototype.GLOBAL_WS_URL = axios.defaults.baseURL.replace(/^http/, 'ws') + '/websocket'
// 拦截请求，设置全局token
axios.interceptors.request.use(function (config) {
  return config
}, function () {
  // 发生错误后执行钩子
  return null
})

axios.interceptors.response.use(function (response) {
  console.log('响应拦截', response)
  return response
}, error => {
  return Promise.reject(error)
})

Vue.use(ElementUI)

Vue.config.productionTip = false

/* eslint-disable */
new Vue({
  el: '#app',
  router,
  components: { App },
  template: '<App/>'
})
