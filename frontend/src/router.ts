import { createRouter, createWebHistory } from 'vue-router'
import ObjectTypeSelector from './components/ObjectTypeSelector.vue'
import CountryList from './components/CountryList.vue'
import DivisionList from './components/DivisionList.vue'
import CandidateList from './components/CandidateList.vue'
import MatchReview from './components/MatchReview.vue'

const routes = [
  {
    path: '/',
    component: ObjectTypeSelector,
  },
  {
    path: '/:typeQid',
    component: CountryList,
    props: true,
  },
  {
    path: '/:typeQid/:countryQid',
    component: DivisionList,
    props: true,
  },
  {
    path: '/:typeQid/:countryQid/:divisionQid',
    component: CandidateList,
    props: true,
  },
  {
    path: '/:typeQid/:countryQid/:divisionQid/:qid',
    component: MatchReview,
    props: true,
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
