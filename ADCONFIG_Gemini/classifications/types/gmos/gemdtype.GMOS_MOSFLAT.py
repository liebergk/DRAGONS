
class GMOS_MOSFLAT(DataClassification):
    name="GMOS_MOSFLAT"
    usage = ""
    parent = "GMOS_CAL"
    requirement = ISCLASS('GMOS_FLAT', 'GMOS_MOS')

newtypes.append(GMOS_MOSFLAT())
