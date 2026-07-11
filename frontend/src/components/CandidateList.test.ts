import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import CandidateList from './CandidateList.vue'
import * as api from '../api'

vi.mock('../api')

const mockedApi = vi.mocked(api, true)

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/:typeQid/:countryQid/:divisionQid/:qid', component: { template: '<div>Match</div>' } }]
})

describe('CandidateList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', async () => {
    mockedApi.getCandidates.mockReturnValue(new Promise(() => {}))
    const wrapper = mount(CandidateList, {
      props: { typeQid: 'Q2143825', countryQid: 'Q34', divisionQid: 'Q504994' },
      global: { plugins: [router] }
    })

    expect(wrapper.text()).toContain('Laddar...')
  })

  it('shows error on API failure', async () => {
    mockedApi.getCandidates.mockRejectedValue(new Error('API Error'))
    const wrapper = mount(CandidateList, {
      props: { typeQid: 'Q2143825', countryQid: 'Q34', divisionQid: 'Q504994' },
      global: { plugins: [router] }
    })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.text()).toContain('Kunde inte ladda kandidater')
  })

  it('renders candidates when data loads', async () => {
    mockedApi.getCandidates.mockResolvedValue([
      { qid: 'Q123', label: 'Trail 1', country_label: 'Sweden' },
      { qid: 'Q456', label: 'Trail 2', country_label: 'Norway' },
    ])
    const wrapper = mount(CandidateList, {
      props: { typeQid: 'Q2143825', countryQid: 'Q34', divisionQid: 'Q504994' },
      global: { plugins: [router] }
    })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    const items = wrapper.findAll('li')
    expect(items.length).toBe(2)
    expect(items[0].text()).toContain('Q123')
    expect(items[0].text()).toContain('Trail 1')
  })

  it('shows empty message when no candidates', async () => {
    mockedApi.getCandidates.mockResolvedValue([])
    const wrapper = mount(CandidateList, {
      props: { typeQid: 'Q2143825', countryQid: 'Q34', divisionQid: 'Q504994' },
      global: { plugins: [router] }
    })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.text()).toContain('Inga kandidater hittades.')
  })

  it('navigates to match page on item click', async () => {
    mockedApi.getCandidates.mockResolvedValue([
      { qid: 'Q123', label: 'Trail 1', country_label: 'Sweden' },
    ])
    const push = vi.fn()
    router.push = push
    const wrapper = mount(CandidateList, {
      props: { typeQid: 'Q2143825', countryQid: 'Q34', divisionQid: 'Q504994' },
      global: { plugins: [router] }
    })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    await wrapper.find('li').trigger('click')

    expect(push).toHaveBeenCalledWith('/Q2143825/Q34/Q504994/Q123')
  })
})
