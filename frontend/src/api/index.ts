import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export interface ObjectTypeInfo {
  object_type: string
  label: string
  qid: string
}

export interface CandidateInfo {
  qid: string
  label: string
  country: string | null
  country_label: string | null
}

export interface CountryInfo {
  qid: string
  label: string
  count: number
}

export interface MatchInfo {
  osm_id: string
  osm_type: string
  osm_name: string
  similarity: number
  osm_url: string
  zoom: number
}

export interface MatchResponse {
  qid: string
  label: string
  matches: MatchInfo[]
  coord: { lat: number; lon: number } | null
}

export async function getObjectTypes(): Promise<ObjectTypeInfo[]> {
  const { data } = await api.get('/types')
  return data
}

export async function getCountries(type: string): Promise<CountryInfo[]> {
  const { data } = await api.get(`/types/${type}/countries`)
  return data
}

export async function getCandidates(type: string, country: string): Promise<CandidateInfo[]> {
  const { data } = await api.get(`/types/${type}/countries/${country}/candidates`)
  return data
}

export async function getMatches(type: string, country: string, qid: string): Promise<MatchResponse> {
  const { data } = await api.get(`/types/${type}/countries/${country}/candidates/${qid}/matches`)
  return data
}

export async function confirmMatch(
  type: string,
  country: string,
  qid: string,
  osmId: string,
  osmType: string,
  osmName: string
): Promise<void> {
  await api.post(`/types/${type}/countries/${country}/candidates/${qid}/confirm`, {
    osm_id: osmId,
    osm_type: osmType,
    osm_name: osmName,
  })
}

export async function rejectMatch(
  type: string,
  country: string,
  qid: string,
  reason?: string
): Promise<void> {
  await api.post(`/types/${type}/countries/${country}/candidates/${qid}/reject`, {
    reason,
  })
}
