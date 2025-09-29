import requests
from datetime import datetime, timedelta, timezone
from obspy import read
import os
import numpy as np
from python_code.print_manager import print_manager

def compute_time_window(days):
    """
    Compute time window based on number of days
    
    Args:
        days (int): Number of days to look back from current time
        
    Returns:
        tuple: (start_str, end_str, alaska_time) for API requests and display
    """
    # 1. Get current UTC time
    utc_now = datetime.now(timezone.utc)
    print_manager.print_time(f"Current UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 2. Calculate end time in UTC
    end_time_utc = utc_now
    
    # 3. Calculate start time by going back specified number of days
    start_time_utc = end_time_utc - timedelta(days=days)
    
    # 4. Format UTC times for the IRIS API
    end_str = end_time_utc.strftime("%Y-%m-%dT%H:%M:%S")
    start_str = start_time_utc.strftime("%Y-%m-%dT%H:%M:%S")
    
    # 5. For display purposes, convert to Alaska time
    # Alaska is UTC-9 standard or UTC-8 during daylight savings
    ak_offset = timedelta(hours=-8)  # Currently in daylight saving
    alaska_time = utc_now + ak_offset
    
    print_manager.print_time(f"Current Alaska time: {alaska_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print_manager.print_api(f"Requesting data from {start_time_utc.strftime('%Y-%m-%d %H:%M:%S')} to {end_time_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # 6. Return the UTC time strings for API and Alaska time for display
    return start_str, end_str, alaska_time

def fetch_seismic_data(start_str, end_str, filename, network="AV", station="SPCN", channel="BHZ"):
    """
    Fetches seismic data from IRIS FDSN web service or loads from existing file
    
    Args:
        start_str (str): Start time in ISO format
        end_str (str): End time in ISO format
        filename (str): Path to save the MiniSEED file
        network (str): Network code
        station (str): Station code
        channel (str): Channel code
        
    Returns:
        obspy.core.stream.Stream: Stream object containing the seismic data
    """
    # Check if file exists locally
    if os.path.exists(filename):
        print_manager.print_file(f"✅ Using existing file: {filename}")
        return read(filename)
    
    # Fetch data from IRIS
    url = "https://service.iris.edu/fdsnws/dataselect/1/query"
    params = {
        "net": network,
        "sta": station,
        "loc": "--",
        "cha": channel,
        "start": start_str,
        "end": end_str,
        "format": "miniseed",
        "nodata": 404
    }
    
    print_manager.print_api(f"Sending request to IRIS: {params}")
    response = requests.get(url, params=params)
    
    # Save if successful
    if response.status_code == 200:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "wb") as f:
            f.write(response.content)
        print_manager.print_file(f"✅ Downloaded and saved file: {filename}")
        
        # Check for data gap issue and split request if needed
        stream = read(filename)
        
        # If we're requesting >12 hours and getting data ending at ~09:52 UTC
        # this indicates the IRIS data gap issue we discovered
        if stream and len(stream) > 0:
            latest_data = stream[0].stats.endtime
            utc_now = datetime.now(timezone.utc)
            
            # Convert end_str to datetime with timezone for proper comparison
            request_end = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S")
            # Make it timezone aware
            request_end = request_end.replace(tzinfo=timezone.utc)
            
            # Convert latest_data from ObsPy UTCDateTime to Python datetime with timezone
            latest_data_dt = datetime(
                latest_data.year, latest_data.month, latest_data.day,
                latest_data.hour, latest_data.minute, latest_data.second,
                latest_data.microsecond, tzinfo=timezone.utc
            )
            
            # If the latest data is >1 hour behind the request end, and around 09:52 UTC
            # This is a heuristic to detect the gap we observed
            gap_hour_threshold = 9  # 09:00 UTC
            gap_hour_max = 10       # 10:00 UTC
            
            time_diff_hours = (request_end - latest_data_dt).total_seconds() / 3600
            if (time_diff_hours > 1 and 
                latest_data.hour >= gap_hour_threshold and 
                latest_data.hour <= gap_hour_max):
                
                print_manager.print_api("Detected potential data gap, fetching more recent data separately...")
                
                # Create a new request from 1 hour after the gap time to now
                second_start = latest_data_dt + timedelta(hours=1)
                second_start_str = second_start.strftime("%Y-%m-%dT%H:%M:%S")
                
                # Create a temporary filename for the second part
                temp_filename = filename.replace(".mseed", "_part2.mseed")
                
                # Second request
                params["start"] = second_start_str
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    with open(temp_filename, "wb") as f:
                        f.write(response.content)
                    
                    # Read the second stream
                    stream2 = read(temp_filename)
                    
                    if stream2 and len(stream2) > 0:
                        print_manager.print_api(f"Additional data found from {stream2[0].stats.starttime} to {stream2[0].stats.endtime}")
                        
                        # Instead of merging streams (which can create masked arrays),
                        # return the two streams as separate traces in the same stream
                        for trace in stream2:
                            stream.append(trace)
                            
                        # Make sure the stream is sorted by starttime
                        stream.sort()
                        
                        # Without merging, just save as is
                        try:
                            stream.write(filename, format="MSEED")
                            print_manager.print_file(f"✅ Combined and saved updated data to: {filename}")
                        except Exception as e:
                            print_manager.print_api(f"Warning: Couldn't save combined stream due to: {e}")
                            print_manager.print_api("Using the streams as they are (unmerged)")
                    
                    # Clean up temporary file
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                
        return stream
    else:
        raise Exception(f"❌ Error {response.status_code}: No data found or request failed.") 