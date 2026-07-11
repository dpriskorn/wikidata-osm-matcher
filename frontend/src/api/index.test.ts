import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import {
  getObjectTypes,
  getCandidates,
  getMatches,
  confirmMatch,
  rejectMatch,
} from './index'

vi.mock('axios')

const mockedAxios = vi.mocked(axios, true)

describe('API Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getObjectTypes', () => {
    it('returns list of object types on success', async () => {
      const mockData = [
        { object_type: 'hiking_trail', label: 'Hiking Trails' },
        { object_type: 'bathing_place', label: 'Bathing Places' },
      ]
      mockedAxios.get.mockResolvedValue({ data: mockData })

      const result = await getObjectTypes()

      expect(result).toEqual(mockData)
      expect(mockedAxios.get).toHaveBeenCalledWith('/api/types')
    })

    it('throws error on API failure', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Network error'))

      await expect(getObjectTypes()).rejects.toThrow('Network error')
    })
  })

  describe('getCandidates', () => {
    it('returns candidates for type', async () => {
      const mockData = [
        { qid: 'Q123', label: 'Trail 1', country_label: 'Sweden' },
        { qid: 'Q456', label: 'Trail 2', country_label: 'Norway' },
      ]
      mockedAxios.get.mockResolvedValue({ data: mockData })

      const result = await getCandidates('hiking_trail')

      expect(result).toEqual(mockData)
      expect(mockedAxios.get).toHaveBeenCalledWith('/api/types/hiking_trail/candidates')
    })

    it('throws error on API failure', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Not found'))

      await expect(getCandidates('hiking_trail')).rejects.toThrow('Not found')
    })
  })

  describe('getMatches', () => {
    it('returns matches for candidate', async () => {
      const mockData = {
        qid: 'Q123',
        label: 'Test Trail',
        matches: [
          { osm_id: '456', osm_type: 'relation', osm_name: 'OSM Trail', similarity: 0.85, osm_url: 'https://www.openstreetmap.org/R/456' },
        ],
      }
      mockedAxios.get.mockResolvedValue({ data: mockData })

      const result = await getMatches('hiking_trail', 'Q123')

      expect(result).toEqual(mockData)
      expect(mockedAxios.get).toHaveBeenCalledWith('/api/types/hiking_trail/candidates/Q123/matches')
    })

    it('returns empty matches array when no matches found', async () => {
      const mockData = { qid: 'Q123', label: 'Test', matches: [] }
      mockedAxios.get.mockResolvedValue({ data: mockData })

      const result = await getMatches('hiking_trail', 'Q123')

      expect(result.matches).toEqual([])
    })

    it('throws error on API failure', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Server error'))

      await expect(getMatches('hiking_trail', 'Q123')).rejects.toThrow('Server error')
    })
  })

  describe('confirmMatch', () => {
    it('posts confirmed match successfully', async () => {
      mockedAxios.post.mockResolvedValue({ status: 200 })

      await confirmMatch('hiking_trail', 'Q123', '456', 'relation', 'Test Trail')

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/types/hiking_trail/candidates/Q123/confirm',
        { osm_id: '456', osm_type: 'relation', osm_name: 'Test Trail' }
      )
    })

    it('throws error on API failure', async () => {
      mockedAxios.post.mockRejectedValue(new Error('Update failed'))

      await expect(confirmMatch('hiking_trail', 'Q123', '456', 'relation', 'Test')).rejects.toThrow('Update failed')
    })
  })

  describe('rejectMatch', () => {
    it('posts rejection successfully', async () => {
      mockedAxios.post.mockResolvedValue({ status: 200 })

      await rejectMatch('hiking_trail', 'Q123')

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/types/hiking_trail/candidates/Q123/reject',
        { reason: undefined }
      )
    })

    it('posts rejection with reason', async () => {
      mockedAxios.post.mockResolvedValue({ status: 200 })

      await rejectMatch('hiking_trail', 'Q123', 'Not a match')

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/types/hiking_trail/candidates/Q123/reject',
        { reason: 'Not a match' }
      )
    })

    it('throws error on API failure', async () => {
      mockedAxios.post.mockRejectedValue(new Error('Server error'))

      await expect(rejectMatch('hiking_trail', 'Q123')).rejects.toThrow('Server error')
    })
  })
})
