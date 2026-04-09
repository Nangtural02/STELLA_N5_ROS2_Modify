std_msgs/Header header
string anchor_id
float64 distance
float64 rssi
float64[] cir
float64 pdr
uint8 status
# status: 0=LOS, 1=NLOS, 255=UNKNOWN
float64 aoa_azimuth        # deg
float64 aoa_elevation      # deg
float64 aoa_azimuth_fom    # % figure of merit
float64 aoa_elevation_fom  # %
