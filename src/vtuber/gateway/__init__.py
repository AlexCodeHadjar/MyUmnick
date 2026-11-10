"""Шлюз: протокол UI ↔ Ядро, кодек, WebSocket-сервер и терминальный чат (M1)."""

from vtuber.gateway.branch_bridge import BranchBridge
from vtuber.gateway.chats_bridge import ChatsBridge
from vtuber.gateway.codec import (
    AUDIO_FRAME_HEADER_SIZE,
    AUDIO_FRAME_TYPE,
    MIC_FRAME_HEADER_SIZE,
    MIC_FRAME_TYPE,
    AudioFrame,
    MicFrame,
    decode_audio_frame,
    decode_inbound,
    decode_mic_frame,
    encode_audio_frame,
    encode_mic_frame,
    encode_outbound,
)
from vtuber.gateway.external_turns import ExternalTurns
from vtuber.gateway.memory_bridge import MemoryBridge
from vtuber.gateway.panels import Panels
from vtuber.gateway.privacy_bridge import PrivacyBridge
from vtuber.gateway.protocol import (
    AvatarEmotion,
    CancelledData,
    ChatCancel,
    ChatDelta,
    ChatSend,
    DeltaData,
    EmotionData,
    ErrorCode,
    ErrorData,
    ErrorMessage,
    InboundMessage,
    InputBargeIn,
    InputFinal,
    InputHypothesis,
    InputTyping,
    MetricsSpan,
    OutboundMessage,
    SendData,
    SpanData,
    Status,
    StatusData,
    TurnCancelledMessage,
    TurnFinishedMessage,
    TurnStartedMessage,
    TypingData,
    turn_ref,
)
from vtuber.gateway.protocol_base import PROTOCOL_VERSION, EmptyData
from vtuber.gateway.protocol_extras import ViewerBlockedMessage
from vtuber.gateway.protocol_presence import AppEdition
from vtuber.gateway.resources_feed import ResourcesFeed
from vtuber.gateway.server import REPLACED_CODE, GatewayConfig, GatewayServer, MicSink
from vtuber.gateway.setup_bridge import SetupBridge
from vtuber.gateway.sink import WsReplySink
from vtuber.gateway.terminal import EXIT_COMMAND, STOP_COMMAND, TerminalChat, TerminalSink
from vtuber.gateway.voice_bridge import END_TO_AUDIO_SPAN, VoiceBridge

__all__ = [
    "AUDIO_FRAME_HEADER_SIZE",
    "AUDIO_FRAME_TYPE",
    "END_TO_AUDIO_SPAN",
    "EXIT_COMMAND",
    "MIC_FRAME_HEADER_SIZE",
    "MIC_FRAME_TYPE",
    "PROTOCOL_VERSION",
    "REPLACED_CODE",
    "STOP_COMMAND",
    "AppEdition",
    "AudioFrame",
    "AvatarEmotion",
    "BranchBridge",
    "CancelledData",
    "ChatCancel",
    "ChatDelta",
    "ChatSend",
    "ChatsBridge",
    "DeltaData",
    "EmotionData",
    "EmptyData",
    "ErrorCode",
    "ErrorData",
    "ErrorMessage",
    "ExternalTurns",
    "GatewayConfig",
    "GatewayServer",
    "InboundMessage",
    "InputBargeIn",
    "InputFinal",
    "InputHypothesis",
    "InputTyping",
    "MemoryBridge",
    "MetricsSpan",
    "MicFrame",
    "MicSink",
    "OutboundMessage",
    "Panels",
    "PrivacyBridge",
    "ResourcesFeed",
    "SendData",
    "SetupBridge",
    "SpanData",
    "Status",
    "StatusData",
    "TerminalChat",
    "TerminalSink",
    "TurnCancelledMessage",
    "TurnFinishedMessage",
    "TurnStartedMessage",
    "TypingData",
    "ViewerBlockedMessage",
    "VoiceBridge",
    "WsReplySink",
    "decode_audio_frame",
    "decode_inbound",
    "decode_mic_frame",
    "encode_audio_frame",
    "encode_mic_frame",
    "encode_outbound",
    "turn_ref",
]
