resource "google_compute_network" "streaming_network" {
  name                    = "streaming-network"
  auto_create_subnetworks = true
}

resource "google_compute_firewall" "allow_internal" {
  name    = "allow-internal"
  network = google_compute_network.streaming_network.name

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/8"]
}

resource "google_compute_firewall" "allow_http_https" {
  name    = "allow-http-https"
  network = google_compute_network.streaming_network.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
}