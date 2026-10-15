import Papa from 'papaparse'

export interface DemoReading {
  Time: string
  Seconds: number
  Drain_46: number
  Drain_53: number
}

const CSV_URL =
  `${import.meta.env.BASE_URL}data/csv/Node_Flood%20Forecast%20DEMO%20SYNTHETIC.csv`

export async function fetchDemoReadings(): Promise<DemoReading[]> {
  const response = await fetch(CSV_URL)

  if (!response.ok) {
    throw new Error(
      `Unable to load demo CSV: ${response.status} ${response.statusText}`
    )
  }

  const csvText = await response.text()

  const result = Papa.parse<DemoReading>(csvText, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (header) => header.trim(),
  })

  if (result.errors.length > 0) {
    throw new Error(
      `CSV parsing failed: ${result.errors[0]?.message ?? 'Unknown parsing error'}`
    )
  }

  return result.data.map((row) => ({
    Time: row.Time,
    Seconds: Number(row.Seconds),
    Drain_46: Number(row.Drain_46),
    Drain_53: Number(row.Drain_53),
  }))
}

export async function fetchDemoContour(
  filename: string
): Promise<GeoJSON.FeatureCollection> {
  const url =
    `${import.meta.env.BASE_URL}data/contours/${encodeURIComponent(filename)}`

  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(
      `Unable to load GeoJSON: ${response.status} ${response.statusText}`
    )
  }

  return response.json()
}