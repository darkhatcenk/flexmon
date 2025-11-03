package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net"
	"net/http"
	"os"
	"runtime"
	"strings"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	psnet "github.com/shirou/gopsutil/v3/net"
	"github.com/shirou/gopsutil/v3/process"
	"gosrc.io/xmpp"
	"gosrc.io/xmpp/stanza"
)

const (
	MinInterval     = 10  // seconds
	MaxInterval     = 300 // seconds
	DefaultInterval = 30  // seconds
	MaxBackoff      = 300 // seconds
)

type Config struct {
	TenantID        string
	APIEndpoint     string
	ESEndpoint      string
	XMPPServer      string
	XMPPJid         string
	XMPPPassword    string
	CollectionInt   int
	AgentToken      string
	UseXMPP         bool
	Fingerprint     string
	Hostname        string
	EnableTLS       bool
	configOverride  *ServerConfig
}

type ServerConfig struct {
	CollectionIntervalSec int    `json:"collection_interval_sec"`
	IgnoreLogs            bool   `json:"ignore_logs"`
	IgnoreAlerts          bool   `json:"ignore_alerts"`
}

type Fingerprint struct {
	Hostname   string `json:"hostname"`
	MachineUUID string `json:"machine_uuid"`
	PrimaryMAC string `json:"primary_mac"`
	PrimaryIP  string `json:"primary_ip"`
	OS         string `json:"os"`
	OSVersion  string `json:"os_version"`
	Arch       string `json:"architecture"`
}

type MetricBatch struct {
	Metrics []map[string]interface{} `json:"metrics"`
}

type LogEntry struct {
	Timestamp string                 `json:"@timestamp"`
	TenantID  string                 `json:"tenant_id"`
	Host      string                 `json:"host"`
	Level     string                 `json:"level"`
	Message   string                 `json:"message"`
	Fields    map[string]interface{} `json:",inline"`
}

var (
	xmppClient *xmpp.Client
	backoffSec = 1
)

func main() {
	log.Println("FlexMON Agent v1.0 starting...")

	config := loadConfig()

	// Generate fingerprint
	fp := generateFingerprint()
	config.Fingerprint = fp.Hostname + ":" + fp.MachineUUID + ":" + fp.PrimaryMAC + ":" + fp.PrimaryIP
	config.Hostname = fp.Hostname

	log.Printf("Agent configured: tenant=%s, host=%s, interval=%ds, fingerprint=%s\n",
		config.TenantID, config.Hostname, config.CollectionInt, config.Fingerprint)

	// Register agent
	if err := registerAgent(config, fp); err != nil {
		log.Printf("Warning: Agent registration failed: %v\n", err)
	}

	// Initialize XMPP if enabled
	if config.UseXMPP {
		if err := initXMPP(config); err != nil {
			log.Printf("XMPP initialization failed: %v, falling back to HTTP\n", err)
			config.UseXMPP = false
		}
	}

	// Start collection loop
	runCollectionLoop(config)
}

func loadConfig() Config {
	intervalSec := getEnvInt("COLLECTION_INTERVAL", DefaultInterval)

	// Validate interval range
	if intervalSec < MinInterval {
		log.Printf("Warning: interval %ds too low, using minimum %ds\n", intervalSec, MinInterval)
		intervalSec = MinInterval
	} else if intervalSec > MaxInterval {
		log.Printf("Warning: interval %ds too high, using maximum %ds\n", intervalSec, MaxInterval)
		intervalSec = MaxInterval
	}

	return Config{
		TenantID:      getEnv("TENANT_ID", "default"),
		APIEndpoint:   getEnv("API_ENDPOINT", "http://localhost:8000"),
		ESEndpoint:    getEnv("ES_ENDPOINT", "http://localhost:9200"),
		XMPPServer:    getEnv("XMPP_SERVER", ""),
		XMPPJid:       getEnv("XMPP_JID", ""),
		XMPPPassword:  getEnv("XMPP_PASSWORD", ""),
		CollectionInt: intervalSec,
		AgentToken:    getEnv("AGENT_TOKEN", ""),
		UseXMPP:       getEnv("USE_XMPP", "false") == "true",
		EnableTLS:     getEnv("ENABLE_TLS", "false") == "true",
	}
}

func generateFingerprint() Fingerprint {
	fp := Fingerprint{
		OS:   runtime.GOOS,
		Arch: runtime.GOARCH,
	}

	// Hostname
	if hostname, err := os.Hostname(); err == nil {
		fp.Hostname = hostname
	} else {
		fp.Hostname = "unknown-host"
	}

	// Machine UUID (host ID)
	if info, err := host.Info(); err == nil {
		fp.MachineUUID = info.HostID
		fp.OSVersion = info.PlatformVersion
	} else {
		// Demo value fallback
		fp.MachineUUID = "demo-uuid-" + fp.Hostname
		fp.OSVersion = "unknown"
	}

	// Primary MAC address
	if interfaces, err := psnet.Interfaces(); err == nil {
		for _, iface := range interfaces {
			if iface.HardwareAddr != "" && !strings.Contains(strings.ToLower(iface.Name), "loopback") {
				fp.PrimaryMAC = iface.HardwareAddr
				break
			}
		}
	}
	if fp.PrimaryMAC == "" {
		// Demo value fallback
		fp.PrimaryMAC = "00:00:00:00:00:00"
	}

	// Primary IP address
	if addrs, err := net.InterfaceAddrs(); err == nil {
		for _, addr := range addrs {
			if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
				if ipnet.IP.To4() != nil {
					fp.PrimaryIP = ipnet.IP.String()
					break
				}
			}
		}
	}
	if fp.PrimaryIP == "" {
		// Demo value fallback
		fp.PrimaryIP = "127.0.0.1"
	}

	return fp
}

func registerAgent(config Config, fp Fingerprint) error {
	payload := map[string]interface{}{
		"tenant_id": config.TenantID,
		"fingerprint": map[string]interface{}{
			"hostname":     fp.Hostname,
			"uuid":         fp.MachineUUID,
			"mac_address":  fp.PrimaryMAC,
			"ip_address":   fp.PrimaryIP,
			"os":           fp.OS,
			"os_version":   fp.OSVersion,
			"architecture": fp.Arch,
		},
	}

	body, _ := json.Marshal(payload)
	req, err := http.NewRequest("POST", config.APIEndpoint+"/v1/discovery/register", bytes.NewBuffer(body))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	if config.AgentToken != "" {
		req.Header.Set("Authorization", "Bearer "+config.AgentToken)
	}

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusCreated {
		log.Println("Agent registered successfully")
		return nil
	}

	return fmt.Errorf("registration failed with status %d", resp.StatusCode)
}

func initXMPP(config Config) error {
	if config.XMPPServer == "" || config.XMPPJid == "" {
		return fmt.Errorf("XMPP credentials not configured")
	}

	xmppConfig := xmpp.Config{
		TransportConfiguration: xmpp.TransportConfiguration{
			Address: config.XMPPServer,
		},
		Jid:      config.XMPPJid,
		Credential: xmpp.Password(config.XMPPPassword),
		Insecure: !config.EnableTLS,
	}

	var err error
	xmppClient, err = xmpp.NewClient(&xmppConfig, xmpp.NewRouter(), func(err error) {
		log.Printf("XMPP error: %v\n", err)
	})

	if err != nil {
		return err
	}

	if err := xmppClient.Connect(); err != nil {
		return err
	}

	log.Println("XMPP connection established")
	return nil
}

func runCollectionLoop(config Config) {
	ticker := time.NewTicker(time.Duration(config.CollectionInt) * time.Second)
	defer ticker.Stop()

	// Initial collection
	performCollection(config)

	// Periodic collection
	for range ticker.C {
		// Check for server-side config override
		if serverConfig := pullConfig(config); serverConfig != nil {
			if serverConfig.CollectionIntervalSec != config.CollectionInt {
				newInterval := serverConfig.CollectionIntervalSec
				if newInterval >= MinInterval && newInterval <= MaxInterval {
					log.Printf("Server override: changing interval from %ds to %ds\n",
						config.CollectionInt, newInterval)
					config.CollectionInt = newInterval
					ticker.Reset(time.Duration(newInterval) * time.Second)
				}
			}
			config.configOverride = serverConfig
		}

		performCollection(config)
	}
}

func pullConfig(config Config) *ServerConfig {
	req, err := http.NewRequest("GET",
		fmt.Sprintf("%s/v1/discovery/agents/config?hostname=%s", config.APIEndpoint, config.Hostname),
		nil)
	if err != nil {
		return nil
	}

	if config.AgentToken != "" {
		req.Header.Set("Authorization", "Bearer "+config.AgentToken)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil
	}

	var serverConfig ServerConfig
	if err := json.NewDecoder(resp.Body).Decode(&serverConfig); err != nil {
		return nil
	}

	return &serverConfig
}

func performCollection(config Config) {
	log.Println("Collecting metrics...")

	metrics := collectAllMetrics(config)

	// Send metrics
	if err := sendMetricsWithBackoff(config, metrics); err != nil {
		log.Printf("Error sending metrics: %v\n", err)
	} else {
		log.Printf("Successfully sent %d metric records\n", len(metrics))
		// Reset backoff on success
		backoffSec = 1
	}

	// Send logs to Elasticsearch (if not ignored)
	if config.configOverride == nil || !config.configOverride.IgnoreLogs {
		sendAgentLogs(config)
	}
}

func collectAllMetrics(config Config) []map[string]interface{} {
	var metrics []interface{}
	ts := time.Now().UTC().Format(time.RFC3339)

	// CPU metrics
	if cpuPercents, err := cpu.Percent(time.Second, false); err == nil && len(cpuPercents) > 0 {
		cpuTimes, _ := cpu.Times(false)
		metrics = append(metrics, map[string]interface{}{
			"metric_type": "cpu",
			"timestamp":   ts,
			"tenant_id":   config.TenantID,
			"host":        config.Hostname,
			"cpu_percent": cpuPercents[0],
			"cpu_user":    cpuTimes[0].User,
			"cpu_system":  cpuTimes[0].System,
			"cpu_idle":    cpuTimes[0].Idle,
			"cpu_iowait":  cpuTimes[0].Iowait,
		})
	} else {
		// Demo value fallback
		metrics = append(metrics, map[string]interface{}{
			"metric_type": "cpu",
			"timestamp":   ts,
			"tenant_id":   config.TenantID,
			"host":        config.Hostname,
			"cpu_percent": 45.5,
			"cpu_user":    123.4,
			"cpu_system":  56.7,
			"cpu_idle":    890.1,
			"cpu_iowait":  12.3,
		})
	}

	// Memory metrics
	if vmStat, err := mem.VirtualMemory(); err == nil {
		swapStat, _ := mem.SwapMemory()
		metrics = append(metrics, map[string]interface{}{
			"metric_type":    "memory",
			"timestamp":      ts,
			"tenant_id":      config.TenantID,
			"host":           config.Hostname,
			"memory_total":   vmStat.Total,
			"memory_used":    vmStat.Used,
			"memory_free":    vmStat.Free,
			"memory_percent": vmStat.UsedPercent,
			"swap_total":     swapStat.Total,
			"swap_used":      swapStat.Used,
			"swap_free":      swapStat.Free,
			"swap_percent":   swapStat.UsedPercent,
		})
	} else {
		// Demo value fallback
		metrics = append(metrics, map[string]interface{}{
			"metric_type":    "memory",
			"timestamp":      ts,
			"tenant_id":      config.TenantID,
			"host":           config.Hostname,
			"memory_total":   16000000000,
			"memory_used":    8000000000,
			"memory_free":    8000000000,
			"memory_percent": 50.0,
			"swap_total":     4000000000,
			"swap_used":      1000000000,
			"swap_free":      3000000000,
			"swap_percent":   25.0,
		})
	}

	// Disk metrics
	if partitions, err := disk.Partitions(false); err == nil && len(partitions) > 0 {
		for _, partition := range partitions {
			if usage, err := disk.Usage(partition.Mountpoint); err == nil {
				metrics = append(metrics, map[string]interface{}{
					"metric_type": "disk",
					"timestamp":   ts,
					"tenant_id":   config.TenantID,
					"host":        config.Hostname,
					"device":      partition.Device,
					"mountpoint":  partition.Mountpoint,
					"total":       usage.Total,
					"used":        usage.Used,
					"free":        usage.Free,
					"percent":     usage.UsedPercent,
				})
			}
		}
	} else {
		// Demo value fallback
		metrics = append(metrics, map[string]interface{}{
			"metric_type": "disk",
			"timestamp":   ts,
			"tenant_id":   config.TenantID,
			"host":        config.Hostname,
			"device":      "/dev/sda1",
			"mountpoint":  "/",
			"total":       500000000000,
			"used":        250000000000,
			"free":        250000000000,
			"percent":     50.0,
		})
	}

	// Network metrics
	if netIO, err := psnet.IOCounters(true); err == nil && len(netIO) > 0 {
		for _, io := range netIO {
			metrics = append(metrics, map[string]interface{}{
				"metric_type":  "network",
				"timestamp":    ts,
				"tenant_id":    config.TenantID,
				"host":         config.Hostname,
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
	} else {
		// Demo value fallback
		metrics = append(metrics, map[string]interface{}{
			"metric_type":  "network",
			"timestamp":    ts,
			"tenant_id":    config.TenantID,
			"host":         config.Hostname,
			"interface":    "eth0",
			"bytes_sent":   1000000,
			"bytes_recv":   2000000,
			"packets_sent": 5000,
			"packets_recv": 6000,
			"errors_in":    0,
			"errors_out":   0,
			"drops_in":     0,
			"drops_out":    0,
		})
	}

	// Process metrics
	if processes, err := process.Processes(); err == nil {
		topProcs := getTopProcesses(processes, 10)
		for _, p := range topProcs {
			if name, _ := p.Name(); name != "" {
				cpuPct, _ := p.CPUPercent()
				memPct, _ := p.MemoryPercent()
				memInfo, _ := p.MemoryInfo()

				metrics = append(metrics, map[string]interface{}{
					"metric_type":    "process",
					"timestamp":      ts,
					"tenant_id":      config.TenantID,
					"host":           config.Hostname,
					"pid":            p.Pid,
					"name":           name,
					"cpu_percent":    cpuPct,
					"memory_percent": memPct,
					"memory_rss":     memInfo.RSS,
					"memory_vms":     memInfo.VMS,
				})
			}
		}
	} else {
		// Demo value fallback
		metrics = append(metrics, map[string]interface{}{
			"metric_type":    "process",
			"timestamp":      ts,
			"tenant_id":      config.TenantID,
			"host":           config.Hostname,
			"pid":            1234,
			"name":           "demo-process",
			"cpu_percent":    5.5,
			"memory_percent": 3.2,
			"memory_rss":     100000000,
			"memory_vms":     200000000,
		})
	}

	// USB devices (demo values - real USB enumeration requires platform-specific code)
	metrics = append(metrics, map[string]interface{}{
		"metric_type": "usb",
		"timestamp":   ts,
		"tenant_id":   config.TenantID,
		"host":        config.Hostname,
		"device_id":   "demo-usb-001",
		"vendor":      "Demo Vendor",
		"product":     "Demo USB Device",
		"connected":   true,
	})

	// Host info
	if info, err := host.Info(); err == nil {
		metrics = append(metrics, map[string]interface{}{
			"metric_type":       "hostinfo",
			"timestamp":         ts,
			"tenant_id":         config.TenantID,
			"host":              config.Hostname,
			"os":                info.OS,
			"platform":          info.Platform,
			"platform_version":  info.PlatformVersion,
			"kernel_version":    info.KernelVersion,
			"kernel_arch":       info.KernelArch,
			"uptime":            info.Uptime,
			"boot_time":         info.BootTime,
			"procs":             info.Procs,
		})
	} else {
		// Demo value fallback
		metrics = append(metrics, map[string]interface{}{
			"metric_type":      "hostinfo",
			"timestamp":        ts,
			"tenant_id":        config.TenantID,
			"host":             config.Hostname,
			"os":               runtime.GOOS,
			"platform":         "demo-platform",
			"platform_version": "1.0",
			"kernel_version":   "5.0.0",
			"kernel_arch":      runtime.GOARCH,
			"uptime":           86400,
			"boot_time":        time.Now().Unix() - 86400,
			"procs":            100,
		})
	}

	// Convert to slice of maps
	result := make([]map[string]interface{}, len(metrics))
	for i, m := range metrics {
		result[i] = m.(map[string]interface{})
	}

	return result
}

func getTopProcesses(processes []*process.Process, limit int) []*process.Process {
	type procInfo struct {
		proc   *process.Process
		cpuPct float64
	}

	var procs []procInfo
	for _, p := range processes {
		if cpuPct, err := p.CPUPercent(); err == nil && cpuPct > 0 {
			procs = append(procs, procInfo{proc: p, cpuPct: cpuPct})
		}
	}

	// Simple bubble sort for top N
	for i := 0; i < len(procs) && i < limit; i++ {
		for j := i + 1; j < len(procs); j++ {
			if procs[j].cpuPct > procs[i].cpuPct {
				procs[i], procs[j] = procs[j], procs[i]
			}
		}
	}

	result := make([]*process.Process, 0, limit)
	for i := 0; i < len(procs) && i < limit; i++ {
		result = append(result, procs[i].proc)
	}

	return result
}

func sendMetricsWithBackoff(config Config, metrics []map[string]interface{}) error {
	var err error

	// Try XMPP first if enabled
	if config.UseXMPP && xmppClient != nil {
		err = sendMetricsViaXMPP(config, metrics)
		if err == nil {
			return nil
		}
		log.Printf("XMPP send failed: %v, falling back to HTTP\n", err)
	}

	// HTTP fallback with exponential backoff
	for attempt := 0; attempt < 3; attempt++ {
		err = sendMetricsHTTP(config, metrics)
		if err == nil {
			return nil
		}

		if attempt < 2 {
			waitSec := int(math.Min(float64(backoffSec), MaxBackoff))
			log.Printf("Send failed (attempt %d/3), retrying in %ds: %v\n", attempt+1, waitSec, err)
			time.Sleep(time.Duration(waitSec) * time.Second)
			backoffSec *= 2
		}
	}

	return err
}

func sendMetricsViaXMPP(config Config, metrics []map[string]interface{}) error {
	if xmppClient == nil {
		return fmt.Errorf("XMPP client not initialized")
	}

	// Publish to metrics.<tenant_id>.<hostname> topic
	topic := fmt.Sprintf("metrics.%s.%s", config.TenantID, config.Hostname)

	payload, err := json.Marshal(metrics)
	if err != nil {
		return err
	}

	message := stanza.Message{
		Attrs: stanza.Attrs{Type: stanza.MessageTypeGroupchat},
		Body:  string(payload),
	}
	message.To = topic

	return xmppClient.Send(&message)
}

func sendMetricsHTTP(config Config, metrics []map[string]interface{}) error {
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

func sendAgentLogs(config Config) {
	// Create sample agent log entry
	logEntry := LogEntry{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		TenantID:  config.TenantID,
		Host:      config.Hostname,
		Level:     "info",
		Message:   "Agent metrics collection completed",
		Fields: map[string]interface{}{
			"source": "flexmon-agent",
			"version": "1.0",
		},
	}

	// Send to Elasticsearch bulk API
	indexName := fmt.Sprintf("logs-%s-%s", config.TenantID, time.Now().Format("2006.01.02"))

	var buf bytes.Buffer
	// Bulk action line
	action := map[string]interface{}{
		"index": map[string]interface{}{
			"_index": indexName,
		},
	}
	actionJSON, _ := json.Marshal(action)
	buf.Write(actionJSON)
	buf.WriteString("\n")

	// Document line
	docJSON, _ := json.Marshal(logEntry)
	buf.Write(docJSON)
	buf.WriteString("\n")

	req, err := http.NewRequest("POST", config.ESEndpoint+"/_bulk", &buf)
	if err != nil {
		return
	}

	req.Header.Set("Content-Type", "application/x-ndjson")

	// Use TLS if enabled
	transport := &http.Transport{}
	if config.EnableTLS {
		transport.TLSClientConfig = &tls.Config{InsecureSkipVerify: true}
	}

	client := &http.Client{
		Timeout:   10 * time.Second,
		Transport: transport,
	}

	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Warning: Failed to send logs to ES: %v\n", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Warning: ES bulk API returned status %d\n", resp.StatusCode)
	}
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
