package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/net"
)

type Config struct {
	TenantID      string
	APIEndpoint   string
	CollectionInt int
	AgentToken    string
}

type MetricRecord struct {
	MetricType string                 `json:"metric_type"`
	Timestamp  string                 `json:"timestamp"`
	TenantID   string                 `json:"tenant_id"`
	Host       string                 `json:"host"`
	Data       map[string]interface{} `json:",inline"`
}

func main() {
	log.Println("FlexMON Agent starting...")

	config := Config{
		TenantID:      getEnv("TENANT_ID", "default"),
		APIEndpoint:   getEnv("API_ENDPOINT", "http://localhost:8000"),
		CollectionInt: getEnvInt("COLLECTION_INTERVAL", 30),
		AgentToken:    getEnv("AGENT_TOKEN", ""),
	}

	hostname, _ := os.Hostname()
	log.Printf("Agent configured: tenant=%s, host=%s, interval=%ds\n",
		config.TenantID, hostname, config.CollectionInt)

	ticker := time.NewTicker(time.Duration(config.CollectionInt) * time.Second)
	defer ticker.Stop()

	// Initial collection
	collectAndSend(config, hostname)

	// Periodic collection
	for range ticker.C {
		collectAndSend(config, hostname)
	}
}

func collectAndSend(config Config, hostname string) {
	log.Println("Collecting metrics...")

	var metrics []interface{}

	// CPU metrics
	if cpuPercents, err := cpu.Percent(time.Second, false); err == nil && len(cpuPercents) > 0 {
		cpuTimes, _ := cpu.Times(false)
		metrics = append(metrics, map[string]interface{}{
			"metric_type": "cpu",
			"timestamp":   time.Now().UTC().Format(time.RFC3339),
			"tenant_id":   config.TenantID,
			"host":        hostname,
			"cpu_percent": cpuPercents[0],
			"cpu_user":    cpuTimes[0].User,
			"cpu_system":  cpuTimes[0].System,
			"cpu_idle":    cpuTimes[0].Idle,
			"cpu_iowait":  cpuTimes[0].Iowait,
		})
	}

	// Memory metrics
	if vmStat, err := mem.VirtualMemory(); err == nil {
		swapStat, _ := mem.SwapMemory()
		metrics = append(metrics, map[string]interface{}{
			"metric_type":    "memory",
			"timestamp":      time.Now().UTC().Format(time.RFC3339),
			"tenant_id":      config.TenantID,
			"host":           hostname,
			"memory_total":   vmStat.Total,
			"memory_used":    vmStat.Used,
			"memory_free":    vmStat.Free,
			"memory_percent": vmStat.UsedPercent,
			"swap_total":     swapStat.Total,
			"swap_used":      swapStat.Used,
			"swap_free":      swapStat.Free,
			"swap_percent":   swapStat.UsedPercent,
		})
	}

	// Disk metrics
	if partitions, err := disk.Partitions(false); err == nil {
		for _, partition := range partitions {
			if usage, err := disk.Usage(partition.Mountpoint); err == nil {
				metrics = append(metrics, map[string]interface{}{
					"metric_type": "disk",
					"timestamp":   time.Now().UTC().Format(time.RFC3339),
					"tenant_id":   config.TenantID,
					"host":        hostname,
					"device":      partition.Device,
					"mountpoint":  partition.Mountpoint,
					"total":       usage.Total,
					"used":        usage.Used,
					"free":        usage.Free,
					"percent":     usage.UsedPercent,
				})
			}
		}
	}

	// Network metrics
	if netIO, err := net.IOCounters(true); err == nil {
		for _, io := range netIO {
			metrics = append(metrics, map[string]interface{}{
				"metric_type":  "network",
				"timestamp":    time.Now().UTC().Format(time.RFC3339),
				"tenant_id":    config.TenantID,
				"host":         hostname,
				"interface":    io.Name,
				"bytes_sent":   io.BytesSent,
				"bytes_recv":   io.BytesRecv,
				"packets_sent": io.PacketsSent,
				"packets_recv": io.PacketsRecv,
				"errors_in":    io.Errin,
				"errors_out":   io.Errout,
				"drops_in":     io.Dropin,
				"drops_out":    io.Dropout,
			})
		}
	}

	// Send metrics
	if err := sendMetrics(config, metrics); err != nil {
		log.Printf("Error sending metrics: %v\n", err)
	} else {
		log.Printf("Successfully sent %d metric records\n", len(metrics))
	}
}

func sendMetrics(config Config, metrics []interface{}) error {
	// Convert to NDJSON
	var buf bytes.Buffer
	for _, metric := range metrics {
		b, _ := json.Marshal(metric)
		buf.Write(b)
		buf.WriteString("\n")
	}

	// Send to API
	req, err := http.NewRequest("POST",
		config.APIEndpoint+"/v1/ingest/metrics/batch",
		&buf)
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/x-ndjson")
	if config.AgentToken != "" {
		req.Header.Set("Authorization", "Bearer "+config.AgentToken)
	}

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("API returned status %d", resp.StatusCode)
	}

	return nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		var intVal int
		fmt.Sscanf(value, "%d", &intVal)
		return intVal
	}
	return defaultValue
}
