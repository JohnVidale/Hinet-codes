#!/usr/bin/env python
# input is set of hinet traces
# this program tapers, filters, selects range and SNR
# plots against traveltime curves, either raw or reduced against traveltimes
# This programs deals with both of repeated events.
# John Vidale 2/2019

def pro3pair(eq_file1, eq_file2, stat_corr = 1, dphase = 'PKIKP', dphase2 = 'PKiKP', dphase3 = 'PKIKP', dphase4 = 'PKiKP',
			start_buff = 200, end_buff = 500,
			plot_scale_fac = 0.05,qual_threshold = 0, corr_threshold = 0,
			freq_min = 1, freq_max = 3, min_dist = 0, max_dist = 180,
			alt_statics = 0, statics_file = 'nothing'):

	from obspy import UTCDateTime
	from obspy import Stream
	from obspy import read
	from obspy.geodetics import gps2dist_azimuth
	import numpy as np
	import os
	from obspy.taup import TauPyModel
	import matplotlib.pyplot as plt
	import time
	model = TauPyModel(model='iasp91')

	import sys # don't show any warnings
	import warnings

	if not sys.warnoptions:
	    warnings.simplefilter("ignore")

	start_time_wc = time.time()

	#%% Get saved event info, also used to name files
	#  event 2016-05-28T09:47:00.000 -56.241 -26.935 78
	file = open(eq_file1, 'r')
	lines=file.readlines()
	split_line = lines[0].split()
#			ids.append(split_line[0])  ignore label for now
	t1           = UTCDateTime(split_line[1])
	date_label1  = split_line[1][0:10]
	ev_lat1      = float(      split_line[2])
	ev_lon1      = float(      split_line[3])
	ev_depth1    = float(      split_line[4])
	print('1st event: date_label ' + date_label1 + ' time ' + str(t1) + ' lat '
	   + str(ev_lat1) + ' lon ' + str( ev_lon1) + ' depth ' + str(ev_depth1))

	file = open(eq_file2, 'r')
	lines=file.readlines()
	split_line = lines[0].split()
#			ids.append(split_line[0])  ignore label for now
	t2           = UTCDateTime(split_line[1])
	date_label2  = split_line[1][0:10]
	ev_lat2      = float(      split_line[2])
	ev_lon2      = float(      split_line[3])
	ev_depth2    = float(      split_line[4])
	print('2nd event: date_label ' + date_label2 + ' time ' + str(t2) + ' lat '
	   + str(ev_lat2) + ' lon ' + str( ev_lon2) + ' depth ' + str(ev_depth2))

	#%% Get Hinet station location file
	if alt_statics == 0: # standard set
		sta_file = '/Users/vidale/Documents/PyCode/Codes/Hinet_station/hinet_master_list.txt'
	else: # custom set made by this event for this event
		sta_file = '/Users/vidale/Documents/PyCode/Hinet/Statics/' + 'HA' + date_label1[:10] + 'pro4_' + dphase + '.statics'
	with open(sta_file, 'r') as file:
		lines = file.readlines()
	print(str(len(lines)) + ' lines read from hinet_master_list')

	# Load station coords into arrays
	station_index = range(len(lines))
	st_names = []
	st_dist  = []
	st_lats  = []
	st_lons  = []
	st_shift = []
	st_corr  = []
	for ii in station_index:
		line = lines[ii]
		split_line = line.split()
		st_names.append(split_line[0])
		st_dist.append(split_line[1])
		st_lats.append( split_line[2])
		st_lons.append( split_line[3])
		st_shift.append(split_line[4])
		st_corr.append(split_line[5])

	#%%
#	stat_corr = 1 # apply station static corrections
	verbose = 0           # more output
	rel_time = 1          # timing is relative to a chosen phase, otherwise relative to OT
#	dphase  = 'PKIKP'       # phase to be aligned
#	dphase2 = 'PKiKP'      # another phase to have traveltime plotted
#	dphase3 = 'pPKiKP'        # another phase to have traveltime plotted
#	dphase4 = 'pPKIKP'        # another phase to have traveltime plotted
#	start_buff = 50       # plots start Xs before PKIKP
#	end_buff   = 200       # plots end Xs before PKIKP
	taper_frac = .05      #Fraction of window tapered on both ends
	signal_dur = 5.       # signal length used in SNR calculation
#	plot_scale_fac = 0.5  #  Bigger numbers make each trace amplitude bigger on plot
#	qual_threshold =  0.2   # minimum SNR
#	corr_threshold = 0.7  # minimum correlation in measuring shift to use station
	plot_tt = 1           # plot the traveltimes?
	do_decimate = 0         # 0 if no decimation desired
#	max_dist = 180
#	min_dist = 0
	#max_dist = 52.5
	#min_dist = 45
#	freq_min = 1
#	freq_max = 3
	ref_loc = 0  # 1 if selecting stations within ref_rad of ref_lat and ref_lon
	             # 0 if selecting stations by distance from earthquake
	if ref_loc == 0:
		ref_lat = 36.3  # °N, around middle of Japan
		ref_lon = 138.5 # °E
		ref_rad = 1.5   # ° radius

	#%% Is taper too long compared to noise estimation window?
	totalt = start_buff + end_buff
	noise_time_skipped = taper_frac * totalt
	if noise_time_skipped >= 0.5 * start_buff:
		print('Specified taper of ' + str(taper_frac * totalt) +
		   ' is not big enough compared to available noise estimation window ' +
		   str(start_buff - noise_time_skipped) + '. May not work well.')
		old_taper_frac = taper_frac
		taper_frac = 0.5*start_buff/totalt
		print('Taper reset from ' + str(old_taper_frac * totalt) + ' to '
		   + str(taper_frac * totalt) + ' seconds.')

	if rel_time == 0: # SNR requirement not implemented for unaligned traces
		qual_threshold = 0

	# Plot with reduced velocity?
	red_plot = 0
	red_dist = 55
	red_time = 300
	red_slow = 7.2 # seconds per degree

	#%% In case one wants to manually enter data here
#	date_label1 = '2008-02-18' # date for filename
#	date_label2 = '2011-02-21' # event has to be unique and in specified 10 minutes
#
#	ev_lon1   = -25.697
#	ev_lat1   = -58.986
#	ev_depth1 = 66.5
#	t1        = UTCDateTime('2008-02-17T19:32:09.100')
#
#	ev_lon2   = -25.696
#	ev_lat2   = -58.986
#	ev_depth2 = 66.5
#	t2        = UTCDateTime('2011-02-20T17:37:45.022')

	#%% Load waveforms
	st1 = Stream()
	st2 = Stream()
	fname1     = 'HD' + date_label1 + '.mseed'
	fname2     = 'HD' + date_label2 + '.mseed'
	st1=read(fname1)
	st2=read(fname2)
	if do_decimate != 0:
		st1.decimate(do_decimate)
		st2.decimate(do_decimate)

	print('1st trace has : ' + str(len(st1[0].data)) + ' time pts ')
	print('st1 has ' + str(len(st1)) + ' traces')
	print('st2 has ' + str(len(st2)) + ' traces')
	print('1st trace starts at ' + str(st1[0].stats.starttime) + ', event at ' + str(t1))
	print('2nd trace starts at ' + str(st2[0].stats.starttime) + ', event at ' + str(t2))

	#%%
	# window and adjust start time to align picked times
	st_pickalign1 = Stream()
	st_pickalign2 = Stream()

	for tr in st1: # traces one by one
		for ii in station_index:
			if (tr.stats.station == st_names[ii]): # find station in inventory
				if stat_corr != 1 or float(st_corr[ii]) > corr_threshold: # if using statics, reject low correlations
					stalat = float(st_lats[ii])
					stalon = float(st_lons[ii])
					if ref_loc == 1:
						ref_distance = gps2dist_azimuth(stalat,stalon,ref_lat,ref_lon)
						ref_dist = ref_distance[0]/(1000*111)
					distance = gps2dist_azimuth(stalat,stalon,ev_lat1,ev_lon1) # Get traveltimes again, hard to store
					tr.stats.distance=distance[0] # distance in km
					dist = distance[0]/(1000*111)
					if ref_loc != 1 and min_dist < dist and dist < max_dist: # select distance range from earthquake
						try:
							arrivals = model.get_travel_times(source_depth_in_km=ev_depth1,distance_in_degree=dist,phase_list=[dphase])
							atime = arrivals[0].time
							if stat_corr == 1: # apply static station corrections
								tr.stats.starttime -= float(st_shift[ii])
							if rel_time == 1:
								s_t = t1 + atime - start_buff
								e_t = t1 + atime + end_buff
							else:
								s_t = t1 - start_buff
								e_t = t1 + end_buff
							tr.trim(starttime=s_t,endtime = e_t)
							# deduct theoretical traveltime and start_buf from starttime
							if rel_time == 1:
								tr.stats.starttime -= atime
							st_pickalign1 += tr
						except:
							pass
					elif ref_loc == 1:
						if ref_dist < ref_rad: # alternatively, select based on distance from ref location
							try:
								arrivals = model.get_travel_times(source_depth_in_km=ev_depth1,distance_in_degree=dist,phase_list=[dphase])
								atime = arrivals[0].time
								if stat_corr == 1: # apply static station corrections
									tr.stats.starttime -= float(st_shift[ii])
								if rel_time == 1:
									s_t = t1 + atime - start_buff
									e_t = t1 + atime + end_buff
								else:
									s_t = t1 - start_buff
									e_t = t1 + end_buff
								tr.trim(starttime=s_t,endtime = e_t)
								# deduct theoretical traveltime and start_buf from starttime
								if rel_time == 1:
									tr.stats.starttime -= atime
								st_pickalign1 += tr
							except:
								pass
	#				if len(tr.data) == 0:
	#					print('Event 1 - empty window.  Trace starts at ' + str(tr.stats.starttime) + ', event at ' + str(t1))

	for tr in st2: # traces one by one
		for ii in station_index:
			if (tr.stats.station == st_names[ii]): # find station in inventory
				if stat_corr != 1 or float(st_corr[ii]) > corr_threshold: # if using statics, reject low correlations
					stalat = float(st_lats[ii])
					stalon = float(st_lons[ii])
					if ref_loc == 1:
						ref_distance = gps2dist_azimuth(stalat,stalon,ref_lat,ref_lon)
						ref_dist = ref_distance[0]/(1000*111)
					distance = gps2dist_azimuth(stalat,stalon,ev_lat2,ev_lon2) # Get traveltimes again, hard to store
					tr.stats.distance=distance[0] # distance in km
					dist = distance[0]/(1000*111)
					if ref_loc != 1 and min_dist < dist and dist < max_dist: # select distance range from earthquake
						try:
							arrivals = model.get_travel_times(source_depth_in_km=ev_depth2,distance_in_degree=dist,phase_list=[dphase])
							atime = arrivals[0].time
							if stat_corr == 1: # apply static station corrections
								tr.stats.starttime -= float(st_shift[ii])
							if rel_time == 1:
								s_t = t2 + atime - start_buff
								e_t = t2 + atime + end_buff
							else:
								s_t = t2 - start_buff
								e_t = t2 + end_buff
							tr.trim(starttime=s_t,endtime = e_t)
							# deduct theoretical traveltime and start_buf from starttime
							if rel_time == 1:
								tr.stats.starttime -= atime
							st_pickalign2 += tr
						except:
							pass
					elif ref_loc == 1:
						if ref_dist < ref_rad: # alternatively, select based on distance from ref location
							try:
								arrivals = model.get_travel_times(source_depth_in_km=ev_depth2,distance_in_degree=dist,phase_list=[dphase])
								atime = arrivals[0].time
								if stat_corr == 1: # apply static station corrections
									tr.stats.starttime -= float(st_shift[ii])
								if rel_time == 1:
									s_t = t2 + atime - start_buff
									e_t = t2 + atime + end_buff
								else:
									s_t = t2 - start_buff
									e_t = t2 + end_buff
								tr.trim(starttime=s_t,endtime = e_t)
								# deduct theoretical traveltime and start_buf from starttime
								if rel_time == 1:
									tr.stats.starttime -= atime
								st_pickalign2 += tr
							except:
								pass
	#				if len(tr.data) == 0:
	#					print('Event 2 - empty window.  Trace starts at ' + str(tr.stats.starttime) + ', event at ' + str(t2))

	print('After alignment and range selection: ' + str(len(st_pickalign1)) + ' traces')

	#%%
	#print(st) # at length
	if verbose:
		print(st1.__str__(extended=True))
		print(st2.__str__(extended=True))
		if rel_time == 1:
			print(st_pickalign1.__str__(extended=True))
			print(st_pickalign2.__str__(extended=True))


	#%%  detrend, taper, filter
	st_pickalign1.detrend(type='simple')
	st_pickalign2.detrend(type='simple')
	st_pickalign1.taper(taper_frac)
	st_pickalign2.taper(taper_frac)
	st_pickalign1.filter('bandpass', freqmin=freq_min, freqmax=freq_max, corners=2, zerophase=True)
	st_pickalign2.filter('bandpass', freqmin=freq_min, freqmax=freq_max, corners=2, zerophase=True)
	st_pickalign1.taper(taper_frac)
	st_pickalign2.taper(taper_frac)

	#%%  Cull further by imposing SNR threshold on both traces
	st1good = Stream()
	st2good = Stream()
	for tr1 in st_pickalign1:
		for tr2 in st_pickalign2:
			if ((tr1.stats.network  == tr2.stats.network) &
			    (tr1.stats.station  == tr2.stats.station)):
	# estimate median noise
				t_noise1_start  = int(len(tr1.data) * taper_frac)
				t_noise2_start  = int(len(tr2.data) * taper_frac)
				t_noise1_end    = int(len(tr1.data) * start_buff/(start_buff + end_buff))
				t_noise2_end    = int(len(tr2.data) * start_buff/(start_buff + end_buff))
				noise1          = np.median(abs(tr1.data[t_noise1_start:t_noise1_end]))
				noise2          = np.median(abs(tr2.data[t_noise2_start:t_noise2_end]))
	# estimate median signal
				t_signal1_start = int(len(tr1.data) * start_buff/(start_buff + end_buff))
				t_signal2_start = int(len(tr2.data) * start_buff/(start_buff + end_buff))
				t_signal1_end   = t_signal1_start + int(len(tr1.data) * signal_dur/(start_buff + end_buff))
				t_signal2_end   = t_signal2_start + int(len(tr2.data) * signal_dur/(start_buff + end_buff))
				signal1         = np.median(abs(tr1.data[t_signal1_start:t_signal1_end]))
				signal2         = np.median(abs(tr2.data[t_signal2_start:t_signal2_end]))
	#			test SNR
				SNR1 = signal1/noise1;
				SNR2 = signal2/noise2;
				if (SNR1 > qual_threshold and SNR2 > qual_threshold):
					st1good += tr1
					st2good += tr2
	#print(st1good)
	#print(st2good)
	print('Above SNR threshold: ' + str(len(st1good)) + ' traces')

	#%%  get station lat-lon, compute distance for plot
	for tr in st1good:
		for ii in station_index:
			if (tr.stats.station == st_names[ii]): # find station in inventory
				stalon = float(st_lons[ii]) # look up lat & lon again to find distance
				stalat = float(st_lats[ii])
				distance = gps2dist_azimuth(stalat,stalon,ev_lat1,ev_lon1)
				tr.stats.distance=distance[0] # distance in km
	for tr in st2good:
		for ii in station_index:
			if (tr.stats.station == st_names[ii]): # find station in inventory
				stalon = float(st_lons[ii]) # look up lat & lon again to find distance
				stalat = float(st_lats[ii])
				distance = gps2dist_azimuth(stalat,stalon,ev_lat2,ev_lon2)
				tr.stats.distance=distance[0] # distance in km

	#%%
	# plot traces
	fig_index = 3
	plt.close(fig_index)
	plt.figure(fig_index,figsize=(10,10))
	plt.xlim(-start_buff,end_buff)
	plt.ylim(min_dist,max_dist)
	for tr in st1good:
		dist_offset = tr.stats.distance/(1000*111) # trying for approx degrees
		ttt = np.arange(len(tr.data)) * tr.stats.delta + (tr.stats.starttime - t1)
		if red_plot == 1:
			shift = red_time + (dist_offset - red_dist) * red_slow
			ttt = ttt - shift
		plt.plot(ttt, (tr.data - np.median(tr.data))*plot_scale_fac /(tr.data.max()
			- tr.data.min()) + dist_offset, color = 'green')
	#plt.title(fname1)

	for tr in st2good:
		dist_offset = tr.stats.distance/(1000*111) # trying for approx degrees
		ttt = np.arange(len(tr.data)) * tr.stats.delta + (tr.stats.starttime - t2)
		if red_plot == 1:
			shift = red_time + (dist_offset - red_dist) * red_slow
			ttt = ttt - shift
		ttt = ttt
#		ttt = ttt + 0.13 # arbitrary eyeballed shift to make plots 1/2 2/1 symetric
		plt.plot(ttt, (tr.data - np.median(tr.data))*plot_scale_fac /(tr.data.max()
			- tr.data.min()) + dist_offset, color = 'red')

		#%% Plot traveltime curves
	if plot_tt:
		# first traveltime curve
		line_pts = 50
		dist_vec  = np.arange(min_dist, max_dist, (max_dist - min_dist)/line_pts) # distance grid
		time_vec1 = np.arange(min_dist, max_dist, (max_dist - min_dist)/line_pts) # empty time grid of same length (filled with -1000)
		for i in range(0,line_pts):
			arrivals = model.get_travel_times(source_depth_in_km=ev_depth1,distance_in_degree
										=dist_vec[i],phase_list=[dphase])
			num_arrivals = len(arrivals)
			found_it = 0
			for j in range(0,num_arrivals):
				if arrivals[j].name == dphase:
					time_vec1[i] = arrivals[j].time
					found_it = 1
			if found_it == 0:
				time_vec1[i] = np.nan
		# second traveltime curve
		if dphase2 != 'no':
			time_vec2 = np.arange(min_dist, max_dist, (max_dist - min_dist)/line_pts) # empty time grid of same length (filled with -1000)
			for i in range(0,line_pts):
				arrivals = model.get_travel_times(source_depth_in_km=ev_depth1,distance_in_degree
											=dist_vec[i],phase_list=[dphase2])
				num_arrivals = len(arrivals)
				found_it = 0
				for j in range(0,num_arrivals):
					if arrivals[j].name == dphase2:
						time_vec2[i] = arrivals[j].time
						found_it = 1
				if found_it == 0:
					time_vec2[i] = np.nan
			if rel_time == 1:
				time_vec2 = time_vec2 - time_vec1
			plt.plot(time_vec2,dist_vec, color = 'orange')
		# third traveltime curve
		if dphase3 != 'no':
			time_vec3 = np.arange(min_dist, max_dist, (max_dist - min_dist)/line_pts) # empty time grid of same length (filled with -1000)
			for i in range(0,line_pts):
				arrivals = model.get_travel_times(source_depth_in_km=ev_depth1,distance_in_degree
											=dist_vec[i],phase_list=[dphase3])
				num_arrivals = len(arrivals)
				found_it = 0
				for j in range(0,num_arrivals):
					if arrivals[j].name == dphase3:
						time_vec3[i] = arrivals[j].time
						found_it = 1
				if found_it == 0:
					time_vec3[i] = np.nan
			if rel_time == 1:
				time_vec3 = time_vec3 - time_vec1
			plt.plot(time_vec3,dist_vec, color = 'yellow')
		# fourth traveltime curve
		if dphase4 != 'no':
			time_vec4 = np.arange(min_dist, max_dist, (max_dist - min_dist)/line_pts) # empty time grid of same length (filled with -1000)
			for i in range(0,line_pts):
				arrivals = model.get_travel_times(source_depth_in_km=ev_depth1,distance_in_degree
											=dist_vec[i],phase_list=[dphase4])
				num_arrivals = len(arrivals)
				found_it = 0
				for j in range(0,num_arrivals):
					if arrivals[j].name == dphase4:
						time_vec4[i] = arrivals[j].time
						found_it = 1
				if found_it == 0:
					time_vec4[i] = np.nan
			if rel_time == 1:
				time_vec4 = time_vec4 - time_vec1
			plt.plot(time_vec4,dist_vec, color = 'purple')

		if rel_time == 1:
			time_vec1 = time_vec1 - time_vec1
		plt.plot(time_vec1,dist_vec, color = 'blue')

	plt.xlabel('Time (s)')
	plt.ylabel('Epicentral distance from event (°)')
	plt.title(dphase + ' for ' + fname1[2:12] + ' vs ' + fname2[2:12])
	#plt.title('Two Sumatra M5.5 quakes, seven years apart, SNR > 15')
	plt.show()

	#  Save processed files
	fname1 = 'HD' + date_label1 + 'sel.mseed'
	fname2 = 'HD' + date_label2 + 'sel.mseed'
	st1good.write(fname1,format = 'MSEED')
	st2good.write(fname2,format = 'MSEED')

	elapsed_time_wc = time.time() - start_time_wc
	print('This job took ' + str(elapsed_time_wc) + ' seconds')
	os.system('say "Done"')