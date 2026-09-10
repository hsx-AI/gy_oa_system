import request from '@/utils/request'

const P = '/travel-itinerary'

export function getTravelItinerarySummary(params) {
  return request({ url: `${P}/summary`, method: 'get', params })
}

export function getTravelItineraryList(params) {
  return request({ url: `${P}/list`, method: 'get', params })
}
