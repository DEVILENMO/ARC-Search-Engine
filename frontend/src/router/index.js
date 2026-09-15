import Vue from 'vue'
import Router from 'vue-router'

Vue.use(Router)

const router = new Router({
  mode: 'history',
  routes: [
    {
      path: '/',
      redirect: 'main'
    },
    {
      path: '/main',
      name: 'main',
      component: () => import('@/view/page/mainPage.vue')
    },
    {
      path: '/res',
      name: 'res',
      component: () => import('@/view/page/resPage.vue')
    }
  ]
})

// 挂载路由导航守卫：to表示将要访问的路径，from表示从哪里来，next是下一个要做的操作
router.beforeEach((to, from, next) => {
  return next()
})
export default router
