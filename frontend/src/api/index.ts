import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export interface ObjectTypeInfo {
  object_type: string
  label: string
  qid: string
  experimental?: boolean
}

export interface CandidateInfo {
  qid: string
  label: string
  country: string | null
  country_label: string | null
  division: string | null
  division_label: string | null
  coord: { lat: number; lon: number } | null
  badkartan?: string
  naturkartan?: string
  commons_p373?: string
  commons_sitelink?: string
}

export interface CountryInfo {
  qid: string
  label: string
  count: number
}

export interface DivisionInfo {
  qid: string
  label: string
  count: number
  lat?: number
  lon?: number
}

export interface MatchInfo {
  osm_id: string
  osm_type: string
  osm_name: string
  similarity: number
  osm_url: string
  zoom: number
  wikidata_match: boolean
  lat: number | null
  lon: number | null
  distance_m: number | null
  property_id: string | null
  tags: Record<string, string>
  needs_investigation: boolean
}

export interface MatchResponse {
  qid: string
  label: string
  matches: MatchInfo[]
  coord: { lat: number; lon: number } | null
  error: string | null
  osm_timestamp: string | null
  badkartan?: string
  naturkartan?: string
  commons_p373?: string
  commons_sitelink?: string
}

export async function getObjectTypes(): Promise<ObjectTypeInfo[]> {
  const { data } = await api.get('/types')
  return data
}

export async function getCountries(type: string): Promise<CountryInfo[]> {
  const { data } = await api.get(`/types/${type}/countries`)
  return data
}

export async function getDivisions(type: string, country: string): Promise<DivisionInfo[]> {
  const { data } = await api.get(`/types/${type}/countries/${country}/divisions`)
  return data
}

export async function getCandidates(type: string, country: string, division: string): Promise<CandidateInfo[]> {
  const { data } = await api.get(`/types/${type}/countries/${country}/divisions/${division}/candidates`)
  return data
}

export async function getMatches(type: string, country: string, division: string, qid: string, radiusKm: number = 0.5): Promise<MatchResponse> {
  const params = radiusKm !== 0.5 ? `?radius_km=${radiusKm}` : ''
  const { data } = await api.get(`/types/${type}/countries/${country}/divisions/${division}/candidates/${qid}/matches${params}`)
  return data
}

export async function confirmMatch(
  type: string,
  country: string,
  division: string,
  qid: string,
  osmId: string,
  osmType: string,
  osmName: string
): Promise<void> {
  await api.post(`/types/${type}/countries/${country}/divisions/${division}/candidates/${qid}/confirm`, {
    osm_id: osmId,
    osm_type: osmType,
    osm_name: osmName,
  })
}

export async function rejectMatch(
  type: string,
  country: string,
  division: string,
  qid: string,
  reason?: string
): Promise<void> {
  await api.post(`/types/${type}/countries/${country}/divisions/${division}/candidates/${qid}/reject`, {
    reason,
  })
}

const USER_AGENT = 'osm-wikidata-matcher-neo 1.0 (https://github.com/anomalyco/opencode)'

export async function getWikidataLabel(qid: string, lang: string = 'en'): Promise<string> {
  const { data } = await api.get(`/wikidata/${qid}/label`, { params: { lang } })
  return data.label
}

export interface AuthStatus {
  logged_in: boolean
  username: string | null
}

export async function getAuthStatus(): Promise<AuthStatus> {
  const { data } = await api.get('/auth/status')
  return data
}

export async function logoutAuth(): Promise<void> {
  await api.post('/auth/logout')
}
