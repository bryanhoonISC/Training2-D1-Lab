/// PatientRequest -> PAT-01 query (QBP^Q22, standard HL7 2.5.1 schema).
Class Insurligent.Interop.DTL.PatientToQBP Extends Ens.DataTransformDTL [ DependsOn = (Insurligent.Interop.MSG.HIS.PatientRequest, EnsLib.HL7.Message) ]
{

Parameter IGNOREMISSINGSOURCE = 1;

Parameter REPORTERRORS = 1;

XData DTL [ XMLNamespace = "http://www.intersystems.com/dtl" ]
{
<transform sourceClass='Insurligent.Interop.MSG.HIS.PatientRequest' targetClass='EnsLib.HL7.Message' targetDocType='2.5.1:QBP_Q21' create='new' language='objectscript' >
<assign value='"D1_IRIS"' property='target.{MSH:SendingApplication.NamespaceID}' action='set' />
<assign value='"D1"' property='target.{MSH:SendingFacility.NamespaceID}' action='set' />
<assign value='"HIS"' property='target.{MSH:ReceivingApplication.NamespaceID}' action='set' />
<assign value='source.HospitalCode' property='target.{MSH:ReceivingFacility.NamespaceID}' action='set' />
<assign value='$Translate($ZDateTime($Horolog,8,1)," :")' property='target.{MSH:DateTimeOfMessage}' action='set' />
<assign value='"QBP"' property='target.{MSH:MessageType.MessageCode}' action='set' />
<assign value='"Q22"' property='target.{MSH:MessageType.TriggerEvent}' action='set' />
<assign value='"QBP_Q21"' property='target.{MSH:MessageType.MessageStructure}' action='set' />
<assign value='"PAT"_$Translate($ZDateTime($Horolog,8,1)," :")' property='target.{MSH:MessageControlID}' action='set' />
<assign value='"P"' property='target.{MSH:ProcessingID.ProcessingID}' action='set' />
<assign value='"2.5.1"' property='target.{MSH:VersionID.VersionID}' action='set' />
<assign value='"PAT-01^GetPatient^L"' property='target.{QPD:MessageQueryName}' action='set' />
<assign value='"Q"_target.{MSH:MessageControlID}' property='target.{QPD:QueryTag}' action='set' />
<assign value='$Translate(source.IdentityNo,"-")_"^^^TH^NI"' property='target.{QPD:UserParametersinsuccessivefi}' action='set' />
<assign value='"I"' property='target.{RCP:QueryPriority}' action='set' />
</transform>
}

}
