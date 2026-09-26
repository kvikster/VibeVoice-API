{ pkgs }:
let
  nemotron = pkgs.fetchurl {
    name = "nemotron-speech-streaming-en-0.6b.q8_0.gguf";
    url = "https://huggingface.co/nvidia/nemotron-speech-streaming-en-0.6b/resolve/ebe59e5a817142986528bbbee5dba8db7b38ed50/nemotron-speech-streaming-en-0.6b.q8_0.gguf?download=true";
    hash = "sha256-2aAYmNKmEch2TiOhwvRecLvVpCXcTek2kqyVHdYDgS0=";
  };
  sortformer = pkgs.fetchurl {
    name = "diar_streaming_sortformer_4spk-v2.q8_0.gguf";
    url = "https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2/resolve/5240a64075176943f677d30fa2171c780229f341/diar_streaming_sortformer_4spk-v2.q8_0.gguf?download=true";
    hash = "sha256-BnnP6xzjVtDeqUcLMSdPS/x+uSdJfYIAVIN3BmbamYo=";
  };
in
pkgs.runCommand "nemotron-sortformer-gguf" { } ''
  mkdir -p $out/share/callevate/models
  ln -s ${nemotron} $out/share/callevate/models/nemotron.gguf
  ln -s ${sortformer} $out/share/callevate/models/sortformer.gguf
''
