/**
 * NoData component - displays Turkish "Veri alınamıyor" message when data is unavailable
 */

interface NoDataProps {
  reason?: string
  height?: number
}

export default function NoData({ reason, height = 260 }: NoDataProps) {
  return (
    <div
      style={{
        height: `${height}px`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#999',
        fontSize: '16px',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px dashed #ddd'
      }}
    >
      <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.3 }}>📊</div>
      <div style={{ fontWeight: '500' }}>Veri alınamıyor</div>
      {reason && import.meta.env.VITE_DEBUG_UI && (
        <div style={{ fontSize: '12px', marginTop: '8px', color: '#ccc' }}>
          ({reason})
        </div>
      )}
    </div>
  )
}
