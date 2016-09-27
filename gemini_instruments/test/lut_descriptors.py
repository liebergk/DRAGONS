import datetime

fixture_data = {
    ('gnirs', 'N20160523S0191.fits'): (
        ('airmass', 1.035),
        ('ao_seeing', None),
        ('array_name', None),
        ('array_section', [0, 1024, 0, 1024]),
        ('azimuth', -54.6193152777778),
        ('camera', 'ShortBlue_G5540'),
        ('cass_rotator_pa', 82.4391422591155),
        ('central_wavelength', 1.6498999999999999e-06),
        ('coadds', 1),
        ('data_label', 'GN-2016A-Q-74-14-007'),
        ('data_section', [0, 1024, 0, 1024]),
        ('dec', 27.928468501322637),
        ('decker', 'SCXD_G5531'),
        ('detector_name', None),
        ('detector_roi_setting', 'Fixed'),
        ('detector_rois_requested', None),
        ('detector_section', [0, 1024, 0, 1024]),
        ('detector_x_bin', 1),
        ('detector_y_bin', 1),
        ('disperser', '32/mm_G5533&SXD_G5536'),
        ('dispersion', None),
        ('dispersion_axis', None),
        ('effective_wavelength', 1.6498999999999999e-06),
        ('elevation', 75.1844152777778),
        ('exposure_time', 115.0),
        ('filter_name', 'Open&XD_G0526'),
        ('focal_plane_mask', '1.00arcsec_G5530&SCXD_G5531'),
        ('gain', 13.5),
        ('gain_setting', None),
        ('gcal_lamp', 'None'),
        ('grating', '32/mm_G5533'),
        ('group_id', 'GN-2016A-Q-74-14_XD_ShortBlue_G5540_Very Faint Objects_Shallow_[0, 1024, 0, 1024]_32/mm&SXD_1.00arcsecXD'),
        ('instrument', 'GNIRS'),
        ('is_ao', False),
        ('is_coadds_summed', True),
        ('local_time', datetime.time(22, 12, 51, 600000)),
        ('lyot_stop', None),
        ('mdf_row_id', None),
        ('nod_count', None),
        ('nod_pixels', None),
        ('nominal_atmospheric_extinction', 0.0),
        ('nominal_photometric_zeropoint', None),
        ('non_linear_level', 4761),
        ('object', 'NGP_1301+2755'),
        ('observation_class', 'science'),
        ('observation_epoch', '2016.39'),
        ('observation_id', 'GN-2016A-Q-74-14'),
        ('observation_type', 'OBJECT'),
        ('overscan_section', None),
        ('pixel_scale', 0.15),
        ('prism', 'SXD_G5536'),
        ('program_id', 'GN-2016A-Q-74'),
        ('pupil_mask', None),
        ('qa_state', 'Pass'),
        ('ra', 195.29060316484365),
        ('raw_bg', 100),
        ('raw_cc', 50),
        ('raw_iq', 70),
        ('raw_wv', 50),
        ('read_mode', 'Very Faint Objects'),
        ('read_noise', 7.0),
        ('read_speed_setting', None),
        ('requested_bg', 100),
        ('requested_cc', 70),
        ('requested_iq', 85),
        ('requested_wv', 100),
        ('saturation_level', 6666),
        ('slit', '1.00arcsec_G5530'),
        ('target_dec', 27.93144167),
        ('target_ra', 195.291925),
        ('telescope', 'Gemini-North'),
        ('ut_date', datetime.date(2016, 5, 23)),
        ('ut_datetime', datetime.datetime(2016, 5, 23, 8, 12, 52, 100000)),
        ('ut_time', datetime.time(8, 12, 52, 100000)),
        ('wavefront_sensor', 'PWFS2'),
        ('wavelength_band', 'H'),
        ('wavelength_reference_pixel', None),
        ('wcs_dec', 27.928468501322637),
        ('wcs_ra', 195.29060316484365),
        ('well_depth_setting', 'Shallow'),
        ('x_offset', 1.48489831646263),
        ('y_offset', 1.39924758216777),
        ),
    ('nifs', 'N20160428S0174.fits') : (
        ('airmass', 1.0),
        ('ao_seeing', None),
        ('array_name', None),
        ('array_section', None),
        ('azimuth', 74.9998625),
        ('camera', 'NIFS'),
        ('cass_rotator_pa', 80.7775052858646),
        ('central_wavelength', 2.2e-06),
        ('coadds', 1),
        ('data_label', 'GN-2016A-FT-9-37-005'),
        ('data_section', [0, 2048, 0, 2048]),
        ('dec', 19.73587494536901),
        ('decker', None),
        ('detector_name', None),
        ('detector_roi_setting', 'Fixed'),
        ('detector_rois_requested', None),
        ('detector_section', None),
        ('detector_x_bin', 1),
        ('detector_y_bin', 1),
        ('disperser', 'K_G5605'),
        ('dispersion', None),
        ('dispersion_axis', None),
        ('effective_wavelength', 2.2e-06),
        ('elevation', 89.9996375),
        ('exposure_time', 900.0),
        ('filter_name', 'Blocked_G0605'),
        ('focal_plane_mask', 'Blocked_G5621'),
        ('gain', 2.4),
        ('gain_setting', None),
        ('gcal_lamp', 'None'),
        ('grating', 'K_G5605'),
        ('group_id', 'GN-2016A-FT-9-37'),
        ('instrument', 'NIFS'),
        ('is_ao', False),
        ('is_coadds_summed', True),
        ('local_time', datetime.time(7, 4, 36, 600000)),
        ('lyot_stop', None),
        ('mdf_row_id', None),
        ('nod_count', None),
        ('nod_pixels', None),
        ('nominal_atmospheric_extinction', 0.0),
        ('nominal_photometric_zeropoint', None),
        ('non_linear_level', 45000),
        ('object', 'Dark'),
        ('observation_class', 'dayCal'),
        ('observation_epoch', '2000.0'),
        ('observation_id', 'GN-2016A-FT-9-37'),
        ('observation_type', 'DARK'),
        ('overscan_section', None),
        ('pixel_scale', None),
        ('prism', None),
        ('program_id', 'GN-2016A-FT-9'),
        ('pupil_mask', None),
        ('qa_state', 'Undefined'),
        ('ra', 317.59292698019476),
        ('raw_bg', None),
        ('raw_cc', None),
        ('raw_iq', None),
        ('raw_wv', None),
        ('read_mode', 'Faint Object'),
        ('read_noise', 1.575),
        ('read_speed_setting', None),
        ('requested_bg', 100),
        ('requested_cc', 100),
        ('requested_iq', 100),
        ('requested_wv', 100),
        ('saturation_level', 50000),
        ('slit', None),
        ('target_dec', 89.96744705328074),
        ('target_ra', 21.999998949631426),
        ('telescope', 'Gemini-North'),
        ('ut_date', datetime.date(2016, 4, 28)),
        ('ut_datetime', datetime.datetime(2016, 4, 28, 17, 4, 37, 100000)),
        ('ut_time', datetime.time(17, 4, 37, 100000)),
        ('wavefront_sensor', None),
        ('wavelength_band', 'K'),
        ('wavelength_reference_pixel', None),
        ('wcs_dec', 19.73587494536901),
        ('wcs_ra', 317.59292698019476),
        ('well_depth_setting', None),
        ('x_offset', 0.0),
        ('y_offset', 0.0)
        ),
}