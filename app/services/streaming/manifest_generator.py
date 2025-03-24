"""
Manifest generator for HLS and DASH streaming formats.
"""

from typing import Dict, Any, List
import xml.etree.ElementTree as ET
from xml.dom import minidom
import math

from app.config import get_settings
from app.core.logging import logger

settings = get_settings()


class ManifestGenerator:
    """
    Generator for HLS and DASH streaming manifest files.
    This service creates master playlists, variant playlists, and MPD files.
    """

    def __init__(self):
        """Initialize the manifest generator."""
        pass

    def generate_hls_master_playlist(self, variant_playlists: List[Dict[str, Any]]) -> str:
        """
        Generate an HLS master playlist.
        
        Args:
            variant_playlists: List of variant playlist data
                Each item should contain:
                - bandwidth: Bandwidth in bits per second
                - resolution: Video resolution (e.g., "1280x720")
                - name: Quality name (e.g., "720p")
            
        Returns:
            Master playlist content as string
        """
        # Start with header
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3"
        ]
        
        # Add each variant
        for variant in variant_playlists:
            # Add stream info
            stream_info = (
                f"#EXT-X-STREAM-INF:BANDWIDTH={variant['bandwidth']},"
                f"RESOLUTION={variant['resolution']}"
            )
            lines.append(stream_info)
            
            # Add playlist filename
            lines.append(f"{variant['name']}.m3u8")
        
        # Join lines to form the playlist
        return "\n".join(lines)

    def generate_hls_variant_playlist(self, segments: List[Dict[str, Any]]) -> str:
        """
        Generate an HLS variant playlist.
        
        Args:
            segments: List of segment data
                Each item should contain:
                - duration: Segment duration in seconds
                - filename: Segment filename
            
        Returns:
            Variant playlist content as string
        """
        # Calculate target duration (ceiling of max segment duration)
        max_duration = max(segment["duration"] for segment in segments)
        target_duration = math.ceil(max_duration)
        
        # Start with header
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f"#EXT-X-TARGETDURATION:{target_duration}",
            "#EXT-X-MEDIA-SEQUENCE:0"
        ]
        
        # Add each segment
        for segment in segments:
            # Add segment info
            duration = segment["duration"]
            filename = segment["filename"]
            
            lines.append(f"#EXTINF:{duration:.6f},")
            lines.append(filename)
        
        # Add end marker
        lines.append("#EXT-X-ENDLIST")
        
        # Join lines to form the playlist
        return "\n".join(lines)

    def generate_dash_mpd(self, adaptation_sets: List[Dict[str, Any]], duration: float) -> str:
        """
        Generate a DASH MPD (Media Presentation Description).
        
        Args:
            adaptation_sets: List of adaptation set data
                Each item should contain:
                - id: Adaptation set ID (e.g., "video_720p")
                - mime_type: MIME type (e.g., "video/mp4")
                - codecs: Codec string (e.g., "avc1.64001f")
                - width: Video width
                - height: Video height
                - bandwidth: Bandwidth in bits per second
                - segment_info: Segment information
            duration: Video duration in seconds
            
        Returns:
            MPD content as string
        """
        # Create MPD root element
        root = ET.Element("MPD")
        root.set("xmlns", "urn:mpeg:dash:schema:mpd:2011")
        root.set("profiles", "urn:mpeg:dash:profile:isoff-live:2011")
        root.set("type", "static")
        root.set("minBufferTime", "PT2S")
        root.set("mediaPresentationDuration", f"PT{duration:.3f}S")
        
        # Create Period element
        period = ET.SubElement(root, "Period")
        period.set("id", "1")
        period.set("start", "PT0S")
        
        # Add each adaptation set
        for adaptation in adaptation_sets:
            # Create AdaptationSet element
            adaptation_set = ET.SubElement(period, "AdaptationSet")
            adaptation_set.set("id", adaptation["id"])
            adaptation_set.set("mimeType", adaptation["mime_type"])
            adaptation_set.set("codecs", adaptation["codecs"])
            adaptation_set.set("startWithSAP", "1")
            
            # Create Representation element
            representation = ET.SubElement(adaptation_set, "Representation")
            representation.set("id", adaptation["id"])
            representation.set("width", str(adaptation["width"]))
            representation.set("height", str(adaptation["height"]))
            representation.set("bandwidth", str(adaptation["bandwidth"]))
            
            # Create SegmentTemplate element
            segment_template = ET.SubElement(representation, "SegmentTemplate")
            segment_template.set("initialization", f"{adaptation['id']}/init.mp4")
            segment_template.set("media", f"{adaptation['id']}/segment-$Number$.m4s")
            segment_template.set("timescale", "1000")
            segment_template.set("startNumber", "1")
            
            # Add SegmentTimeline if provided
            if "segment_timeline" in adaptation:
                segment_timeline = ET.SubElement(segment_template, "SegmentTimeline")
                
                for segment in adaptation["segment_timeline"]:
                    s = ET.SubElement(segment_timeline, "S")
                    s.set("t", str(segment["start"]))
                    s.set("d", str(segment["duration"]))
            else:
                # Use segment duration attribute if no timeline
                segment_template.set("duration", str(int(settings.DASH_SEGMENT_DURATION * 1000)))
        
        # Convert to pretty XML string
        xml_str = ET.tostring(root, encoding="utf-8")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        return pretty_xml

    def generate_hls_live_playlist(self, segments: List[Dict[str, Any]], sequence_no: int) -> str:
        """
        Generate an HLS live playlist (no EXT-X-ENDLIST).
        
        Args:
            segments: List of recent segment data
            sequence_no: Media sequence number
            
        Returns:
            Live playlist content as string
        """
        # Calculate target duration (ceiling of max segment duration)
        max_duration = max(segment["duration"] for segment in segments)
        target_duration = math.ceil(max_duration)
        
        # Start with header
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f"#EXT-X-TARGETDURATION:{target_duration}",
            f"#EXT-X-MEDIA-SEQUENCE:{sequence_no}"
        ]
        
        # Add each segment
        for segment in segments:
            # Add segment info
            duration = segment["duration"]
            filename = segment["filename"]
            
            lines.append(f"#EXTINF:{duration:.6f},")
            lines.append(filename)
        
        # No end marker for live streams
        
        # Join lines to form the playlist
        return "\n".join(lines)

    def generate_dash_live_mpd(self, adaptation_sets: List[Dict[str, Any]], now: int) -> str:
        """
        Generate a DASH live MPD.
        
        Args:
            adaptation_sets: List of adaptation set data
            now: Current time in milliseconds
            
        Returns:
            MPD content as string
        """
        # Create MPD root element
        root = ET.Element("MPD")
        root.set("xmlns", "urn:mpeg:dash:schema:mpd:2011")
        root.set("profiles", "urn:mpeg:dash:profile:isoff-live:2011")
        root.set("type", "dynamic")
        root.set("minBufferTime", "PT2S")
        root.set("timeShiftBufferDepth", "PT30S")
        root.set("availabilityStartTime", "1970-01-01T00:00:00Z")
        root.set("publishTime", self._format_time(now))
        
        # Create Period element
        period = ET.SubElement(root, "Period")
        period.set("id", "1")
        period.set("start", "PT0S")
        
        # Add each adaptation set
        for adaptation in adaptation_sets:
            # Create AdaptationSet element
            adaptation_set = ET.SubElement(period, "AdaptationSet")
            adaptation_set.set("id", adaptation["id"])
            adaptation_set.set("mimeType", adaptation["mime_type"])
            adaptation_set.set("codecs", adaptation["codecs"])
            adaptation_set.set("startWithSAP", "1")
            
            # Create Representation element
            representation = ET.SubElement(adaptation_set, "Representation")
            representation.set("id", adaptation["id"])
            representation.set("width", str(adaptation["width"]))
            representation.set("height", str(adaptation["height"]))
            representation.set("bandwidth", str(adaptation["bandwidth"]))
            
            # Create SegmentTemplate element
            segment_template = ET.SubElement(representation, "SegmentTemplate")
            segment_template.set("initialization", f"{adaptation['id']}/init.mp4")
            segment_template.set("media", f"{adaptation['id']}/segment-$Number$.m4s")
            segment_template.set("timescale", "1000")
            segment_template.set("startNumber", str(adaptation.get("start_number", 1)))
            
            # Add SegmentTimeline
            segment_timeline = ET.SubElement(segment_template, "SegmentTimeline")
            
            for segment in adaptation["segment_timeline"]:
                s = ET.SubElement(segment_timeline, "S")
                s.set("t", str(segment["start"]))
                s.set("d", str(segment["duration"]))
        
        # Convert to pretty XML string
        xml_str = ET.tostring(root, encoding="utf-8")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        return pretty_xml

    def _format_time(self, ms: int) -> str:
        """
        Format time in milliseconds to ISO 8601 format.
        
        Args:
            ms: Time in milliseconds
            
        Returns:
            Formatted time string
        """
        import datetime
        dt = datetime.datetime.utcfromtimestamp(ms / 1000)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")