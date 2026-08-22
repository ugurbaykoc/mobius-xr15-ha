# Mobius C2 Protocol Reference

Extracted from the official **Mobius Android app v2.26** (`com.c2development.mobius`, versionCode 120) by static analysis of `classes3.dex`. Every table below comes from the app's own enums — `com.c2.comm.M$C2Attribute`, `M$VisualID`, `M$SceneID` and friends — not from guesswork, so these are the names and IDs the firmware itself uses.

> Reproduce: unpack the XAPK, take `com.c2development.mobius.apk`, extract `classes3.dex`, and read the `<clinit>` of the enums under `Lcom/c2/comm/M$...;`.

## Schedule interpolation (settled)

`com.c2.comm.model.schedule.PointSchedule.getIntensitiesAtTime(int, boolean)` interpolates **linearly** between consecutive points: it computes `slope = (v2 - v1) / (t2 - t1)`, then `value(t) = slope * t + (v1 - slope * t1)`, rounded. The schedule is **cyclic across midnight** — the last point is mirrored at `t - 1440` before the first and the first at `t + 1440` after the last, so 23:30 → 00:00 fades smoothly rather than snapping.

Consequence for this project: a schedule with few points still produces smooth ramps. Points define the *shape*; the device fills in every minute between them. There is no staircase to design around.

## Frame format

```
02 | DE | msg_id(2B LE) | 00 00 | payload_len(2B LE) | payload | crc16(2B LE)
```

- `0xDE` = request magic, `0xDF` = response magic
- opcode `0x17` = GET, `0x18` = SET
- CRC16 covers everything from the magic byte through the payload

**GET payload** that actually returns data: `attr_id(2B LE) + sub(1B) + count(1B)`. A bare `attr_id` returns a single status byte (`0x0d`) instead of a value — verified against a real device.

**SET payload**: `attr_id(2B LE) + sub(1B) + count(1B) + elem_len(1B) + data`.

**Schedule slot** (element of attribute 500), 42 bytes: `time_minutes(2B LE) + flags(1B) + 13 × [visual_id(1B) + value(2B LE)]`. Values are 0–1000. 25 slots per schedule, written 8 at a time to stay inside the 517-byte MTU.

## Channels — `M$VisualID`

The 13 entries in a schedule slot are these IDs. Note the last two are **not LEDs**: they are per-slot weather probabilities, which is why an XR15 slot carries 13 entries for 10 physical colours.

| ID | Name | Notes |
|---|---|---|
| 1 | Brightness | master dimmer — 0 blanks the whole slot regardless of colours |
| 16 | CoolWhite | present on XR15w G5 Pro |
| 17 | Blue | present on XR15w G5 Pro |
| 18 | RoyalBlue | present on XR15w G5 Pro |
| 19 | Green | present on XR15w G5 Pro |
| 20 | Red | present on XR15w G5 Pro |
| 21 | UV | present on XR15w G5 Pro |
| 22 | WarmWhite | present on XR15w G5 Pro |
| 23 | Violet | present on XR15w G5 Pro |
| 24 | DeepBlue |  |
| 25 | DeepRed |  |
| 26 | NeutralWhite |  |
| 27 | Yellow |  |
| 28 | Amber |  |
| 29 | FarRed |  |
| 30 | Moonlight |  |
| 31 | MoonlightWhite | previously unidentified in this repo |
| 32 | MoonlightBlue | present on XR15w G5 Pro |
| 33 | Cyan |  |
| 34 | Lime |  |
| 35 | BlueAndWhite |  |
| 36 | RedAndWhite |  |
| 37 | UV_PLUS |  |
| 38 | White |  |
| 100 | StormProbability | weather sim, not an LED |
| 101 | CloudProbability | weather sim, not an LED |

## Attributes — `M$C2Attribute` (345 total)

The ones this project uses or could use next:

| ID | Name | Why it matters |
|---|---|---|
| 1 | FirmwareVersion | firmware version |
| 3 | SerialNumber | serial number |
| 4 | Model | model |
| 101 | PhysicalValues | live telemetry — see PhysicalValues |
| 104 | OperationState | OOB / LiveDemo / Scene / Schedule |
| 107 | ErrorState | see ErrorState |
| 200 | IsClockSet | is the device clock set at all |
| 203 | MinuteOfDay | minute of day — the device clock the schedule runs on |
| 303 | Signal | signal |
| 400 | ConfiguredScenes | scene definitions |
| 401 | CurrentScene | instant scene — see SceneID (FeedMode, AllOff, Thunderstorm…) |
| 500 | Schedule1 | the 25-slot schedule we write |
| 501 | Schedule1Checksum | checksum of schedule 1 |
| 502 | Schedule1StartTime | schedule start time |
| 503 | Schedule2 | a **second** schedule |
| 506 | Schedule2ActiveDays | day-of-week mask for schedule 2 |
| 507 | CurrentSchedule | which schedule is playing |
| 508 | CurrentScheduleElement | which element is active — real state readback instead of optimistic |
| 509 | ActiveConfiguration | active configuration |
| 510 | SchedulePlayback | playback control (see SchedulePlaybackAction) |
| 511 | Schedule1Intensity | global intensity multiplier we use for on/off/brightness |
| 901 | SupportedColorChannels | which colour channels this unit actually has |
| 902 | AcclimationEnabled | coral acclimation ramp |
| 903 | AcclimationPeriod | acclimation period |
| 904 | AcclimationStartIntensity | acclimation start intensity |
| 907 | LunarPhasesEnabled | lunar cycle simulation |
| 909 | LunarPhasesCurrentScalar | current lunar scalar |
| 910 | MaxFanSpeed | max fan speed |
| 912 | InsolationEnabled | insolation (seasonal) enable |
| 913 | InsolationTable1 | insolation table |
| 1403 | MaintenanceDue | device's own maintenance-due flag |
| 1507 | FanOnTemperature | fan-on temperature |
| 1511 | PuckTemperature | LED puck temperature |

<details><summary>Full 345-attribute table</summary>

| ID | Name |
|---|---|
| 0 | AttributeTableVersion |
| 1 | FirmwareVersion |
| 2 | HardwareRevision |
| 3 | SerialNumber |
| 4 | Model |
| 5 | Name |
| 6 | Reset |
| 7 | Identify |
| 8 | PrimitiveType |
| 9 | NumberOfFsciInstances |
| 10 | MaxFSCIPacketSize |
| 11 | BootCounter |
| 12 | CRCAttributes |
| 13 | CRCFunction |
| 14 | SupportedAttributesCRC |
| 15 | NumberOfPrimitives |
| 100 | ADCValues |
| 101 | PhysicalValues |
| 102 | PowerState |
| 103 | MACAddress |
| 104 | OperationState |
| 105 | OperationMode |
| 106 | SyncTo |
| 107 | ErrorState |
| 108 | GroupBitmap |
| 109 | PINCode |
| 111 | ConfiguredShortAddress |
| 112 | ConfiguredThreadEUI |
| 113 | ConfiguredThreadChannel |
| 114 | ConfiguredThreadRole |
| 115 | ConfiguredThreadPANID |
| 116 | ConfiguredThreadXPANID |
| 117 | ConfiguredThreadNetworkName |
| 118 | ConfiguredThreadPSKd |
| 119 | ConfiguredThreadMasterKey |
| 120 | ConfiguredThreadMLPrefix |
| 121 | PreferedNetworkInterface |
| 122 | HMISecurityEnabled |
| 123 | ExternalBroadcastControlled |
| 200 | IsClockSet |
| 201 | Epoch |
| 202 | TimeZoneOffset |
| 203 | MinuteOfDay |
| 204 | ClockErrorCount |
| 205 | PosixTimeZoneString |
| 206 | OlsonTimeZoneLocation |
| 207 | LocalTime |
| 208 | TimeSyncDiff |
| 209 | RingID |
| 210 | TimeSyncParentIP |
| 211 | LastSyncTime |
| 212 | LastSyncRequestTime |
| 213 | LastReceivedBeaconTime |
| 214 | LastSentBeaconTime |
| 215 | Uptime |
| 216 | ConnectCount |
| 217 | EpochHighResolution |
| 218 | LocalTimeHighResolution |
| 219 | RTCTime |
| 300 | LocalControlEnabled |
| 301 | AutoDimTimeout |
| 302 | ButtonPressSceneID |
| 303 | Signal |
| 400 | ConfiguredScenes |
| 401 | CurrentScene |
| 402 | SceneTimeout |
| 403 | SceneTimer |
| 404 | LiveDemoSceneNero |
| 405 | LiveDemoTimeout |
| 406 | LiveDemoTimer |
| 407 | LiveDemoScene |
| 408 | ConfiguredScenesChecksum |
| 500 | Schedule1 |
| 501 | Schedule1Checksum |
| 502 | Schedule1StartTime |
| 503 | Schedule2 |
| 504 | Schedule2Checksum |
| 505 | Schedule2StartTime |
| 506 | Schedule2ActiveDays |
| 507 | CurrentSchedule |
| 508 | CurrentScheduleElement |
| 509 | ActiveConfiguration |
| 510 | SchedulePlayback |
| 511 | Schedule1Intensity |
| 512 | Schedule2Intensity |
| 600 | RemoteNotificationsEnabled |
| 601 | SupportedRemoteNotifications |
| 602 | RemoteNotificationConfiguration |
| 603 | PendingNotifications |
| 604 | ReportConfiguration |
| 700 | MotorSpeed |
| 701 | BatteryBackupMaxSpeed |
| 702 | FeedModeMaxSpeed |
| 703 | MaxFaultCount |
| 704 | FaultClearTimeout |
| 705 | PumpOverrideMode |
| 706 | BatteryBackupSpeed |
| 707 | MinimumGallonsPerHour |
| 708 | MaximumGallonsPerHour |
| 717 | CoffeeLedOn |
| 800 | PowerOnDelay |
| 801 | ClosedLoop |
| 802 | FeedModeReturnDelay |
| 803 | BoostedBatteryPower |
| 804 | BoostedBatteryPowerOnTime |
| 805 | BoostedBatteryPowerOffTime |
| 900 | GroupMaster |
| 901 | SupportedColorChannels |
| 902 | AcclimationEnabled |
| 903 | AcclimationPeriod |
| 904 | AcclimationStartIntensity |
| 905 | AcclimationStartTime |
| 907 | LunarPhasesEnabled |
| 908 | LunarPhasesCurrentDay |
| 909 | LunarPhasesCurrentScalar |
| 910 | MaxFanSpeed |
| 911 | IsGroupMaster |
| 912 | InsolationEnabled |
| 913 | InsolationTable1 |
| 914 | InsolationTable2 |
| 915 | InsolationTableInfo |
| 1000 | ThreadLeaderIP |
| 1001 | NetworkedThreadDevices |
| 1002 | DeleteNetworkThreadDevice |
| 1003 | RFFrequency |
| 1004 | LinkLocalAddresses |
| 1005 | MeshLocalAddresses |
| 1006 | RoutingLocatorAddresses |
| 1007 | GlobalUnicastAddresses |
| 1008 | AnycastAddresses |
| 1009 | AllIPv6Addresses |
| 1010 | AllThreadNodesAddresses |
| 1011 | TimeSyncDifference |
| 1012 | TimeSyncCorrections |
| 1100 | LegacyDeviceAddress |
| 1101 | LegacyDeviceSubnet |
| 1102 | LegacyModelNumber |
| 1103 | LegacyCPUType |
| 1104 | LegacyUpdateOffChipMicro |
| 1105 | LegacyUpdateOffChipMicroFWRev |
| 1106 | LegacyUpdateOffChipMicroState |
| 1107 | LegacyStatusObtained |
| 1108 | LegacySerialNumber |
| 1200 | MainMicroTempRaw |
| 1201 | MainMicroBandGapRaw |
| 1202 | MainMicroTempCalibration |
| 1203 | FanShutdownEnabled |
| 1204 | ChannelCurrent |
| 1205 | RTCTrimValue |
| 1206 | MemoryStatistics |
| 1207 | EngineeringCommand |
| 1208 | PanicInformation |
| 1209 | SetDebugLevel |
| 1210 | ClearDebugLevel |
| 1211 | DebugLevelMask |
| 1212 | ManualMode |
| 1213 | DebugPortMode |
| 1214 | RTCClockOutMode |
| 1215 | PumpMotorOffDebug |
| 1216 | CommunicationQueueCountAverage |
| 1217 | CommunicationQueueFullCount |
| 1218 | CommunicationTimerStartFailures |
| 1219 | CommunicationTimerStopFailures |
| 1220 | CommunicationTimerExpirationFailures |
| 1221 | CommunicationTimeout |
| 1222 | CommunicationBadResponseCount |
| 1223 | CommunicationRequestResetCount |
| 1224 | CommunicationResponseResetCount |
| 1225 | NVMLoadStatus |
| 1226 | UpdatedPriorToLastBoot |
| 1227 | ReadMemoryAddress |
| 1228 | ReadMemoryData |
| 1229 | WriteMemoryAddress |
| 1230 | WriteMemoryData |
| 1231 | FCCRegulatoryMode |
| 1232 | FCCRegulatoryTransmitPower |
| 1300 | IsCalibrated |
| 1301 | CalibrationCommand |
| 1302 | CalibrationState |
| 1303 | CalibrationStatus |
| 1304 | LastCalibrationTime |
| 1305 | ZeroFlowPower |
| 1306 | MaxTrimPower |
| 1307 | NumberOfChannelsForCalibration |
| 1308 | MinCalibratedSpeed |
| 1309 | MaxCalibratedSpeed |
| 1400 | RecommendedMaintenanceInterval |
| 1401 | MaintenanceTimer |
| 1402 | LastMaintenanceTime |
| 1403 | MaintenanceDue |
| 1500 | Intensity |
| 1501 | Flash |
| 1502 | Pulse |
| 1503 | StatusLEDMode |
| 1504 | MaxPower |
| 1505 | Ramp |
| 1506 | Set |
| 1507 | FanOnTemperature |
| 1508 | FanOffTemperature |
| 1509 | EnterShutdownTemperature |
| 1510 | ExitShutdownTemperature |
| 1511 | PuckTemperature |
| 1512 | PuckTemperatureLimits |
| 1513 | NormalPower |
| 1600 | BLEMTU |
| 1601 | BLEConnectionInterval |
| 1602 | DeviceInterrogated |
| 1603 | BLEAddress |
| 1604 | DiscoveryIndication |
| 1700 | Temperature |
| 1701 | Humidity |
| 1702 | CO2Status |
| 1703 | CO2PPM |
| 1909 | DriverVersion |
| 2000 | SSID |
| 2001 | Passphrase |
| 2002 | Security |
| 2003 | WifiAction |
| 2004 | WifiStatus |
| 2005 | WifiMacAddress |
| 2006 | IPAddress |
| 2007 | NetworkMask |
| 2008 | Gateway |
| 2009 | InterfaceName |
| 2010 | InterfaceType |
| 2011 | IPAddressMode |
| 2012 | CurrentChannel |
| 2013 | WifiRSSI |
| 2014 | WifiOperationMode |
| 2015 | ShadowIPAddress |
| 2016 | ShadowNetworkMask |
| 2017 | ShadowGateway |
| 2100 | RandomExtendedAddress |
| 2101 | ShortAddress |
| 2102 | ScanChannelMask |
| 2103 | ScanDuration |
| 2104 | Channel |
| 2105 | PanID |
| 2106 | ExtendedPanID |
| 2107 | PermitJoin |
| 2108 | RXOnWhenIdle |
| 2109 | PollInterval |
| 2110 | UniqueExtendedAddress |
| 2111 | VendorName |
| 2112 | ModelName |
| 2113 | SoftwareVersion |
| 2114 | StackVersion |
| 2115 | NetworkCapabilities |
| 2116 | NetworkName |
| 2117 | ThreadDeviceType |
| 2118 | IsDeviceConnected |
| 2119 | IsDeviceCommissioned |
| 2120 | PartitionID |
| 2121 | DeviceRole |
| 2122 | NetworkMasterKey |
| 2123 | NetworkKeySequence |
| 2124 | PSKc |
| 2125 | PSKd |
| 2126 | VendorData |
| 2127 | EDTimeoutPeriod |
| 2128 | MLPrefix |
| 2129 | WhiteListEntry |
| 2132 | KeyRotationInterval |
| 2133 | ChildAddressMask |
| 2134 | SEDTimeoutPeriod |
| 2135 | ChildEDRequestFullNetworkData |
| 2136 | IsFastPollEnabled |
| 2137 | SEDFastPollInterval |
| 2138 | JoinLQIThreshold |
| 2139 | ProvisioningURL |
| 2140 | SelectBestChannelEDThreshold |
| 2149 | SteeringData |
| 2151 | KeySwitchGuardTime |
| 2152 | ParentHoldTime |
| 2153 | SecurityPolicy |
| 2154 | NVMRestoreAutoStart |
| 2155 | NVMRestore |
| 2156 | SLAACPolicy |
| 2157 | IEEExtendedAddress |
| 2158 | LeaderWeight |
| 2164 | HashIEEEAddress |
| 2165 | DoNotGeneratePartitionID |
| 2180 | BRGlobalOnMeshPrefix |
| 2181 | BRDefaultRouteOnMeshPrefix |
| 2182 | BRExternalIfPrefix |
| 2196 | MeshCopActiveTimestamp |
| 2197 | MeshCopPendingChannel |
| 2198 | MeshCopPendingChannelMask |
| 2199 | MeshCopPendingXpanID |
| 2200 | MeshCopPendingMLPrefix |
| 2201 | MeshCopPendingNetworkMasterKey |
| 2202 | MeshCopPendingNetworkName |
| 2203 | MeshCopPendingPanID |
| 2204 | MeshCopPendingPSKc |
| 2205 | MeshCopPendingSecurityPolicy |
| 2206 | MeshCopPendingNetworkKeyRotationInterval |
| 2207 | MeshCopPendingDelayTimer |
| 2208 | MeshCopPendingActiveTimestamp |
| 2209 | MeshCopPendingTimestamp |
| 2210 | MeshCopPendingCommissionerID |
| 2211 | JoinerUDPPort |
| 2212 | CommissionerUDPPort |
| 2213 | DiscoveryRequestMacTXOptions |
| 2214 | MinimumDelayTime |
| 2300 | DoseApplication |
| 2301 | DailyDosage |
| 2302 | MaxDoseRate |
| 2303 | MaxDosagePerDay |
| 2304 | DoseScheduleType |
| 2305 | DoseSensorType |
| 2310 | ContainerMonitorOption |
| 2312 | ContainerVolume |
| 2313 | ContainerCurrentVolume |
| 2314 | DoseInformation |
| 2315 | CurrentDosage |
| 2316 | DoseApplicationColor |
| 2317 | Primed |
| 2318 | PumpPosition |
| 2319 | RemoteButtonAction |
| 2320 | BaseSerialNumber |
| 2321 | RunCurrent |
| 2322 | HaltState |
| 2329 | DoseHistory |
| 2700 | ConstArray |
| 2701 | RAMArray |
| 2702 | NVMArray |
| 2703 | FNArray |
| 2704 | ConstList |
| 2705 | RAMList |
| 2706 | NVMList |
| 2707 | FNList |
| 3600 | RelayState |
| 3700 | ShortAddressArray |
| 3701 | SerialNumberArray |
| 3702 | DeviceModelArray |
| 3703 | FirmwareVersionArray |
| 3704 | ErrorStateArray |
| 3705 | VisualIntensityArray |
| 3706 | PingPresentArray |
| 3712 | BladeShortAddress |
| 3713 | MxmBleAddress |
| 3714 | BladeBleAddressArray |
| 4100 | CoffeeStatusIntensity |
| 4101 | CoffeeFeedModeReturnDelay |
| 4102 | CoffeePowerOnDelay |

</details>

## Playback actions — `M$SchedulePlaybackAction`

Written to attribute 510. This project sends `01 00` = StartResume with an undefined duration.

| ID | Name |
|---|---|
| 0 | Undefined |
| 1 | StartResume |
| 2 | PauseUpdate |
| 3 | Stop |

## Playback durations — `M$SchedulePlaybackDuration`

Second byte of the 510 payload.

| ID | Name |
|---|---|
| 0 | Undefined |
| 1 | ThirtySeconds |
| 2 | SixtySeconds |
| 3 | NinetySeconds |
| 4 | OneHundredTwentySeconds |

## Scenes — `M$SceneID`

Written to attribute 401. These are instant effects that need no schedule write at all.

| ID | Name |
|---|---|
| 0 | EmptyScene |
| 1 | FeedMode |
| 2 | BatteryBackup |
| 3 | AllOff |
| 4 | ColorCycle |
| 5 | Disco |
| 6 | Thunderstorm |
| 7 | CloudCover |
| 8 | AllOn |
| 9 | All50 |

## Ramp shapes — `M$RampType`

| ID | Name |
|---|---|
| 1 | Sinusoidal |
| 2 | Logarithmic |
| 3 | Linear |

## Telemetry — `M$PhysicalValues`

Indices into attribute 101. Readable sensors.

| ID | Name |
|---|---|
| 0 | Unknown |
| 1 | DriverTemperature |
| 2 | MotorTemperature |
| 3 | ClusterTemperature |
| 4 | MotorPower |
| 5 | MotorRPM |
| 6 | BatteryVoltage |
| 7 | InputVoltage |
| 8 | InternalTemperature |
| 9 | FanSpeed |
| 10 | MotorTemperatureFromStaterResistor |
| 11 | GallonsPerHour |
| 12 | SupplyCurrent |
| 13 | FanVoltage |
| 14 | ModuleTemperature |
| 15 | MotorSpinning |
| 16 | Cluster2Temperature |

## Error states — `M$ErrorState`

Attribute 107.

| ID | Name |
|---|---|
| 0 | NoError |
| 1 | Disconnect |
| 2 | Temperature |
| 3 | Stall |
| 4 | Thermistor |
| 5 | UnderVoltage |
| 6 | PowerSupply |
| 7 | SchedulePlayback |
| 8 | OverVoltage |
| 9 | OverCurrent |
| 10 | LockDetectionCurrentLimit |
| 11 | AbnormalSpeed |
| 12 | AbnormalKt |
| 13 | StuckInOpenLoop |
| 14 | StuckInClosedLoop |
| 15 | FanFault |
| 16 | DriverTemp |
| 17 | LEDChannelShortCircuit |
| 18 | LEDChannelCurrentLeak |
| 19 | LEDChannelOpenCircuit |
| 20 | LEDClusterThermistor |
| 21 | LEDClusterOverTemp |
| 22 | DeviceBricked |
| 23 | RTC |
| 32 | DriverPowerSection |
| 33 | DoseInitSpiInit |
| 34 | DoseInitMutexCreate |
| 35 | DoseInitRegisterInit |
| 36 | DoseInitTaskCreate |
| 37 | DoseInitCorruptHome |
| 38 | DoseInitNeedsToCompleteDockingWarning |
| 39 | DoseStartDoseInProgress |
| 40 | DoseStartDriverError |
| 41 | DoseStartMaxDoseVolumeExceeded |
| 42 | DoseStartMaxDoseRateExceeded |
| 43 | DoseStartMinDoseRateExceeded |
| 44 | DoseStartParameterCalculation |
| 45 | DoseStartAccelerationTime |
| 46 | DoseStartSpiCommError |
| 47 | DoseStartPositionOutOfSync |
| 48 | DoseStopDriverError |
| 49 | DoseStopSpiComm |
| 50 | DoseStatusError |
| 51 | DoseGetPowerDownInfoError |
| 52 | DoseSetHome |
| 53 | DoseCalibrationNoCalibrationDoseInfo |
| 54 | DoseCalibrationParamOutOfRange |
| 64 | MotorPowerDip |
| 65 | MotorShort |
| 67 | Wireless |
| 68 | AppUpgrade |
| 69 | ClogError |
| 79 | DryRun |
| 128 | PTCTrip |

## Operation state — `M$OperationState`

Attribute 104 — what the device is doing right now.

| ID | Name |
|---|---|
| 0 | OOB |
| 1 | LiveDemo |
| 2 | Scene |
| 3 | Schedule |
