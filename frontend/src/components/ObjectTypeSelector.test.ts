import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import ObjectTypeSelector from './ObjectTypeSelector.vue'
import * as api from '../api'

vi.mock('../api')

const mockedApi = vi.mocked(api, true)

describe('ObjectTypeSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', async () => {
    mockedApi.getObjectTypes.mockReturnValue(new Promise(() => {}))
    const wrapper = mount(ObjectTypeSelector)

    expect(wrapper.text()).toContain('Laddar...')
  })

  it('shows error on API failure', async () => {
    mockedApi.getObjectTypes.mockRejectedValue(new Error('API Error'))
    const wrapper = mount(ObjectTypeSelector)

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.text()).toContain('Kunde inte ladda objekttyper')
  })

  it('renders type buttons when data loads', async () => {
    mockedApi.getObjectTypes.mockResolvedValue([
      { object_type: 'hiking_trail', label: 'Hiking Trails' },
      { object_type: 'bathing_place', label: 'Bathing Places' },
    ])
    const wrapper = mount(ObjectTypeSelector)

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBe(2)
    expect(buttons[0].text()).toBe('Hiking Trails')
    expect(buttons[1].text()).toBe('Bathing Places')
  })

  it('emits select event with object_type on button click', async () => {
    mockedApi.getObjectTypes.mockResolvedValue([
      { object_type: 'hiking_trail', label: 'Hiking Trails' },
    ])
    const wrapper = mount(ObjectTypeSelector)

    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r, 0))

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')?.[0]).toEqual(['hiking_trail'])
  })
})
