/// Empirically confirmed from a real RV400 capture (see the Python toolkit's
/// `analyzers.gatt` output on that capture: service handles 80-88,
/// characteristic value_handle=82 with write+notify, observed carrying
/// "PAIR...#" writes and "ACCEPTED"/telemetry notifications) — not guessed.
/// Mirrors `revolt_ble_toolkit.live.client` on the Python side exactly.
const kVehicleControlServiceUuid = '49535343-fe7d-4ae5-8fa9-9fafd205e455';
const kVehicleControlCharacteristicUuid =
    '49535343-1e4d-4bd9-ba61-23c647249616';

const kPairAcceptedResponse = 'ACCEPTED';
