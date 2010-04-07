
class GMOS_TWOSLIT(DataClassification):
    name="GMOS_TWOSLIT"
    usage = ""
    parent = "GMOS_IFU"
    requirement = ISCLASS('GMOS_IFU') & PHU(MASKNAME='(IFU-2)|(IFU-2-NS)')

newtypes.append(GMOS_TWOSLIT())
