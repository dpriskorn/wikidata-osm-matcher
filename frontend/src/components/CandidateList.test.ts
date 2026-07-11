import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import CandidateList from './CandidateList.vue'
import * as api from '../api'

vi.mock('../api')

const mockedApi = vi.mocked(api, true)

describe('CandidateList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', async () => {
    mockedApi.getCandidates.mockReturnValue(new Promise(() => {}))
    const wrapper = mount(CandidateList, { props: { type: 'hiking_trail' } })

    expect(wrapper.text()).toContain('Laddar...')
  })

  it('shows error on API failure', async () => {
    mockedApi.getCandidates.mockRejectedValue(new Error('API Error'))
    const wrapper = mount(CandidateList, { props: { type: 'hiking_trail' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.text()).toContain('Kunde inte ladda kandidater')
  })

  it('renders candidates when data loads', async () => {
    mockedApi.getCandidates.mockResolvedValue([
      { qid: 'Q123', label: 'Trail 1', country_label: 'Sweden' },
      { qid: 'Q456', label: 'Trail 2', country_label: 'Norway' },
    ])
    const wrapper = mount(CandidateList, { props: { type: 'hiking_trail' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    const items = wrapper.findAll('li')
    expect(items.length).toBe(2)
    expect(items[0].text()).toContain('Q123')
    expect(items[0].text()).toContain('Trail 1')
  })

  it('shows empty message when no candidates', async () => {
    mockedApi.getCandidates.mockResolvedValue([])
    const wrapper = mount(CandidateList, { props: { type: 'hiking_trail' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.text()).toContain('Inga objekt hittades')
  })

  it('emits select with qid on item click', async () => {
    mockedApi.getCandidates.mockResolvedValue([
      { qid: 'Q123', label: 'Trail 1', country_label: 'Sweden' },
    ])
    const wrapper = mount(CandidateList, { props: { type: 'hiking_trail' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    await wrapper.find('li').trigger('click')

    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')?.[0]).toEqual(['Q123'])
  })

  it('hides country when null', async () => {
    mockedApi.getCandidates.mockResolvedValue([
      { qid: 'Q123', label: 'Trail 1', country_label: null },
    ])
    const wrapper = mount(CandidateList, { props: { type: 'hiking_trail' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.find('.country').exists()).toBe(false)
  })
})
