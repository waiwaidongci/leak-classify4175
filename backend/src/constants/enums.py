from enum import StrEnum
class Role(StrEnum):
 ADMIN='admin'
 ANALYST='analyst'
 VIEWER='viewer'
class RunStatus(StrEnum):
 QUEUED='queued'
 RUNNING='running'
 SUCCEEDED='succeeded'
 FAILED='failed'
class PolicyStatus(StrEnum):
 DRAFT='draft'
 APPROVED='approved'
 REJECTED='rejected'
class Verdict(StrEnum):
 PENDING='pending'
 CONFIRMED='confirmed'
 FALSE_ALARM='false_alarm'
