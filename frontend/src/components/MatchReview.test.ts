import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import MatchReview from './MatchReview.vue'
import * as api from '../api'

vi.mock('../api')

const mockedApi = vi.mocked(api, true)

describe('MatchReview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows loading state initially', async () => {
    mockedApi.getMatches.mockReturnValue(new Promise(() => {}))
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    expect(wrapper.text()).toContain('Laddar...')
  })

  it('shows error on API failure', async () => {
    mockedApi.getMatches.mockRejectedValue(new Error('API Error'))
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.text()).toContain('Kunde inte ladda matcher')
  })

  it('renders matches when data loads', async () => {
    mockedApi.getMatches.mockResolvedValue({
      qid: 'Q123',
      label: 'Test Trail',
      matches: [
        { osm_id: '456', osm_type: 'relation', osm_name: 'OSM Trail', similarity: 0.85, osm_url: 'https://www.openstreetmap.org/R/456' },
      ],
    })
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.text()).toContain('Test Trail')
    expect(wrapper.text()).toContain('OSM Trail')
  })

  it('shows high similarity badge for >= 0.7', async () => {
    mockedApi.getMatches.mockResolvedValue({
      qid: 'Q123',
      label: 'Test',
      matches: [{ osm_id: '456', osm_type: 'relation', osm_name: 'Trail', similarity: 0.85, osm_url: 'https://www.openstreetmap.org/R/456' }],
    })
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.find('.similarity.high').exists()).toBe(true)
  })

  it('shows medium similarity badge for >= 0.5 and < 0.7', async () => {
    mockedApi.getMatches.mockResolvedValue({
      qid: 'Q123',
      label: 'Test',
      matches: [{ osm_id: '456', osm_type: 'relation', osm_name: 'Trail', similarity: 0.6, osm_url: 'https://www.openstreetmap.org/R/456' }],
    })
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.find('.similarity.medium').exists()).toBe(true)
  })

  it('shows low similarity badge for < 0.5', async () => {
    mockedApi.getMatches.mockResolvedValue({
      qid: 'Q123',
      label: 'Test',
      matches: [{ osm_id: '456', osm_type: 'relation', osm_name: 'Trail', similarity: 0.4, osm_url: 'https://www.openstreetmap.org/R/456' }],
    })
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.find('.similarity.low').exists()).toBe(true)
  })

  it('shows no matches message when matches empty', async () => {
    mockedApi.getMatches.mockResolvedValue({ qid: 'Q123', label: 'Test', matches: [] })
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.text()).toContain('Inga OSM-kandidater hittades')
  })

  it('emits back event on back button click', async () => {
    mockedApi.getMatches.mockResolvedValue({ qid: 'Q123', label: 'Test', matches: [] })
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('back')).toBeTruthy()
  })

  it('opens Wikidata link in new tab', async () => {
    mockedApi.getMatches.mockResolvedValue({ qid: 'Q123', label: 'Test', matches: [] })
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    const link = wrapper.find('.link-btn')
    expect(link.attributes('target')).toBe('_blank')
  })

  it('confirm calls API and navigates back on success', async () => {
    mockedApi.getMatches.mockResolvedValue({
      qid: 'Q123',
      label: 'Test',
      matches: [{ osm_id: '456', osm_type: 'relation', osm_name: 'Trail', similarity: 0.85, osm_url: 'https://www.openstreetmap.org/R/456' }],
    })
    mockedApi.confirmMatch.mockResolvedValue()
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    await wrapper.find('.confirm-btn').trigger('click')
    await wrapper.vm.$nextTick()

    expect(mockedApi.confirmMatch).toHaveBeenCalledWith('hiking_trail', 'Q123', '456', 'relation', 'Trail')
    expect(wrapper.text()).toContain('Matchning sparad!')
  })

  it('reject calls API and navigates back on success', async () => {
    mockedApi.getMatches.mockResolvedValue({ qid: 'Q123', label: 'Test', matches: [] })
    mockedApi.rejectMatch.mockResolvedValue()
    const wrapper = mount(MatchReview, { props: { type: 'hiking_trail', qid: 'Q123' } })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    await wrapper.find('.reject-btn').trigger('click')
    await wrapper.vm.$nextTick()

    expect(mockedApi.rejectMatch).toHaveBeenCalledWith('hiking_trail', 'Q123', undefined)
    expect(wrapper.text()).toContain('Markerad som "ingen match"')
  })
})
