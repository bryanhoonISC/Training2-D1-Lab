/// PAT-01 reply (RSP^K22, standard HL7 2.5.1 schema) -> PatientResponse.
/// The reply fits the 2.5.1 structure RSP_K22. In it, PID is inside the repeating
/// group PIDgrp, so the paths start with PIDgrp(1).PID. (RSP_K21 needs a QRI
/// segment, and the HIS does not send one.)
Class Insurligent.Interop.DTL.RSPToPatient Extends Ens.DataTransformDTL [ DependsOn = (EnsLib.HL7.Message, Insurligent.Interop.MSG.HIS.PatientResponse) ]
{

Parameter IGNOREMISSINGSOURCE = 1;

Parameter REPORTERRORS = 1;

XData DTL [ XMLNamespace = "http://www.intersystems.com/dtl" ]
{
<transform sourceClass='EnsLib.HL7.Message' targetClass='Insurligent.Interop.MSG.HIS.PatientResponse' sourceDocType='2.5.1:RSP_K22' create='new' language='objectscript' >
<code>
<annotation>The HL7 operation does not set the message type of a reply. Set it, so the paths below work.</annotation>
<![CDATA[ Do source.PokeDocType("2.5.1:RSP_K22")]]></code>
<assign value='$Select(source.{QAK:QueryResponseStatus}="OK":"200",1:"404")' property='target.ResponseCode' action='set' />
<assign value='$Select(target.ResponseCode="200":"Success",1:"Patient not found in the HIS")' property='target.ResponseMessage' action='set' />
<assign value='source.{PIDgrp(1).PID:PatientIdentifierList(1).IDNumber}' property='target.HospitalNumber' action='set' />
<assign value='source.{PIDgrp(1).PID:PatientName(1).GivenName}' property='target.FirstName' action='set' />
<assign value='source.{PIDgrp(1).PID:PatientName(1).FamilyName}' property='target.LastName' action='set' />
<assign value='source.{PIDgrp(1).PID:DateTimeofBirth}' property='target.BirthDate' action='set' />
<assign value='source.{PIDgrp(1).PID:AdministrativeSex}' property='target.Gender' action='set' />
</transform>
}

}
