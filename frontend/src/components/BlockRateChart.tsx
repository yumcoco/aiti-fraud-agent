import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

interface Decision {
  decision: string
  created_at: string
}

interface Props {
  decisions: Decision[]
}

export default function BlockRateChart({ decisions }: Props) {
  const data = useMemo(() => {
    if (decisions.length === 0) return []

    const byMinute: Record<string, { total: number; blocked: number }> = {}

    decisions.forEach(d => {
      if (!d.created_at) return
      const date = new Date(d.created_at)
      const key = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
      if (!byMinute[key]) byMinute[key] = { total: 0, blocked: 0 }
      byMinute[key].total += 1
      if (d.decision === 'block') byMinute[key].blocked += 1
    })

    return Object.entries(byMinute)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([time, counts]) => ({
        time,
        rate: counts.total > 0
          ? parseFloat(((counts.blocked / counts.total) * 100).toFixed(2))
          : 0,
      }))
  }, [decisions])

  return (
    <div style={{
      background: 'var(--surface)',
      borderRadius: 'var(--radius)',
      border: '0.5px solid var(--border)',
      padding: 12,
    }}>
      <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 8 }}>
        Block rate — by minute
      </div>
      {data.length === 0 ? (
        <div style={{
          height: 80,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: 12,
        }}>
          No data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={80}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 9, fill: '#AAAAAA' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 9, fill: '#AAAAAA' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={v => `${v}%`}
              width={32}
            />
            <Tooltip
              formatter={(v: number) => [`${v}%`, 'Block rate']}
              contentStyle={{ fontSize: 11, border: '0.5px solid var(--border)', borderRadius: 4 }}
            />
            <Line
              type="monotone"
              dataKey="rate"
              stroke="#FF6200"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}