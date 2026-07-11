import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ObjectTypeSelector from './ObjectTypeSelector.vue'
import * as api from '../api'

vi.mock('../api')

const mockedApi = vi.mocked(api, true)

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/:typeQid', component: { template: '<div>Country</div>' } }]
})

describe('ObjectTypeSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', async () => {
    mockedApi.getObjectTypes.mockReturnValue(new Promise(() => {}))
    const wrapper = mount(ObjectTypeSelector, {
      global: { plugins: [router] }
    })

    expect(wrapper.text()).toContain('Laddar...')
  })

  it('shows error on API failure', async () => {
    mockedApi.getObjectTypes.mockRejectedValue(new Error('API Error'))
    const wrapper = mount(ObjectTypeSelector, {
      global: { plugins: [router] }
    })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.text()).toContain('Kunde inte ladda objekttyper')
  })

  it('renders type buttons when data loads', async () => {
    mockedApi.getObjectTypes.mockResolvedValue([
      { object_type: 'hiking_trail', label: 'Hiking Trails', qid: 'Q2143825' },
      { object_type: 'bathing_place', label: 'Bathing Places', qid: 'Q567998' },
    ])
    const wrapper = mount(ObjectTypeSelector, {
      global: { plugins: [router] }
    })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBe(2)
    expect(buttons[0].text()).toBe('Hiking Trails')
    expect(buttons[1].text()).toBe('Bathing Places')
  })

  it('navigates on button click', async () => {
    mockedApi.getObjectTypes.mockResolvedValue([
      { object_type: 'hiking_trail', label: 'Hiking Trails', qid: 'Q2143825' },
    ])
    const push = vi.fn()
    router.push = push
    const wrapper = mount(ObjectTypeSelector, {
      global: { plugins: [router] }
    })

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    await wrapper.find('button').trigger('click')

    expect(push).toHaveBeenCalledWith('/Q2143825')
  })
})
