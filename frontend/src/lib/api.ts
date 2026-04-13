// frontend/src/lib/api.ts
// Single source of truth for all backend URLs.
// Set VITE_API_URL in your .env.production when deploying.

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export const API = {
  stations:                          `${BASE_URL}/api/stations`,
  classify:                          `${BASE_URL}/api/classify`,
  latestCpcbData:                    `${BASE_URL}/api/latest-cpcb-data`,
  anomalyHeatmap:                    `${BASE_URL}/api/anomaly-heatmap`,
  daynightList:                      `${BASE_URL}/api/daynight/list`,
  daynightImage: (stationId: string) => `${BASE_URL}/static/daynight/station_${stationId}.png`,
  correlation:   (stationId: string, method: string) => `${BASE_URL}/api/correlation/${stationId}?method=${method}`,
  dailyPred:     (stationId: string) => `${BASE_URL}/api/predictions/daily/${stationId}`,
  weeklyPred:    (stationId: string) => `${BASE_URL}/api/predictions/weekly/${stationId}`,
  weeklyDetails: (stationId: string) => `${BASE_URL}/api/predictions/weekly_details/${stationId}`,
  dailySummary:                      `${BASE_URL}/api/predictions/summary/daily`,
  weeklySummary:                     `${BASE_URL}/api/predictions/summary/weekly`,
};