{ pkgs, cuda ? false }:
let
  inherit (pkgs) lib;
  darwin = pkgs.stdenv.hostPlatform.isDarwin;
  source = pkgs.fetchFromGitHub {
    owner = "NVIDIA";
    repo = "NeMo-Speech.cpp";
    rev = "97a15afa5caa9bce5baaa86c1184103877af4101";
    hash = "sha256-6QEaSsyQFTRxN0/PpUSYM6X5CksL9ngCpgaGKsirIAs=";
  };
  ggml = pkgs.fetchFromGitHub {
    owner = "ggml-org";
    repo = "ggml";
    rev = "c03b4e2bcece5134827881af90242086daf75be5";
    hash = "sha256-jTEuxEVZLNJ2r86SAiQXp2w3ZTznwRlIr27iqkeUY7E=";
  };
  rivaCommon = pkgs.fetchFromGitHub {
    owner = "nvidia-riva";
    repo = "common";
    rev = "71df98266725320a6b6b3a9f32a6da832dc93691";
    hash = "sha256-f9W/5vTHgAi7E5qRj8xubnBToQlSCzWEBANzcsI3H3Q=";
  };
  # nixpkgs' static SentencePiece bundles an old protobuf; exporting it from
  # libnemo_speech_asr makes every Riva request fail protobuf deserialization.
  sentencepiece = pkgs.sentencepiece.overrideAttrs (old: {
    buildInputs = (old.buildInputs or []) ++ [ pkgs.protobuf pkgs.abseil-cpp ];
    cmakeFlags = (old.cmakeFlags or []) ++ [
      "-DSPM_PROTOBUF_PROVIDER=package"
      "-DSPM_ABSL_PROVIDER=package"
    ];
    postPatch = (old.postPatch or "") + ''
      substituteInPlace src/CMakeLists.txt \
        --replace-fail 'find_package(Protobuf REQUIRED)' \
          'find_package(Protobuf REQUIRED)
  set(PROTOBUF_LITE_LIBRARY protobuf::libprotobuf)'
    '';
  });
in
pkgs.stdenv.mkDerivation {
  pname = "nemo-riva-asr";
  version = "0.1.0-97a15af";
  src = source;

  nativeBuildInputs = with pkgs; [ cmake ninja pkg-config git protobuf grpc ]
    ++ lib.optionals cuda [ pkgs.cudaPackages.cuda_nvcc ];
  buildInputs = with pkgs; [ abseil-cpp protobuf grpc ] ++ [ sentencepiece ]
    ++ lib.optionals cuda [
      pkgs.cudaPackages.cuda_cudart
      pkgs.cudaPackages.libcublas
      pkgs.cudaPackages.cccl
    ];

  postPatch = ''
    rm -rf ggml proto/riva-common
    cp -R ${ggml} ggml
    cp -R ${rivaCommon} proto/riva-common
    chmod -R u+w ggml proto/riva-common
    # Upstream's gRPC guard requires TTS even though riva_server gates it off.
    substituteInPlace CMakeLists.txt \
      --replace-fail '(NOT NEMO_SPEECH_BUILD_ASR OR NOT NEMO_SPEECH_BUILD_TTS)' \
        'NOT NEMO_SPEECH_BUILD_ASR' \
      --replace-fail 'NEMO_SPEECH_BUILD_GRPC currently requires both ASR and TTS' \
        'NEMO_SPEECH_BUILD_GRPC requires ASR'
    cat >> src/asr/CMakeLists.txt <<'CMAKE'

# The Nix SentencePiece archive uses the same external protobuf as Riva.
# Link its dependencies explicitly: upstream only does this for vcpkg/Windows.
find_package(protobuf CONFIG REQUIRED)
find_package(absl CONFIG REQUIRED)
target_link_libraries(nemo_speech_asr PRIVATE protobuf::libprotobuf
  absl::status absl::strings absl::flags absl::flags_parse absl::log absl::check)
CMAKE
  '' + lib.optionalString cuda ''
    bash scripts/apply-ggml-patches.sh
  '';

  cmakeFlags = [
    "-DNEMO_SPEECH_BUILD_ASR=ON"
    "-DNEMO_SPEECH_BUILD_DIAR=ON"
    "-DNEMO_SPEECH_BUILD_TTS=OFF"
    "-DNEMO_SPEECH_BUILD_NMT=OFF"
    "-DNEMO_SPEECH_BUILD_CLI=OFF"
    "-DNEMO_SPEECH_BUILD_MIC_CAPTURE=OFF"
    "-DNEMO_SPEECH_BUILD_HTTP=OFF"
    "-DNEMO_SPEECH_BUILD_GRPC=ON"
    "-DNEMO_SPEECH_GRPC_USE_CONFIG=ON"
    "-DNEMO_SPEECH_BUILD_TESTS=OFF"
    "-DNEMO_SPEECH_BUILD_EXAMPLES=OFF"
    "-DNEMO_SPEECH_BUILD_TOOLS=OFF"
    "-DGGML_METAL=${if darwin then "ON" else "OFF"}"
    "-DGGML_CUDA=${if cuda then "ON" else "OFF"}"
    "-DNEMO_SPEECH_GGML_PATCHED=${if cuda then "ON" else "OFF"}"
  ] ++ lib.optionals cuda [
    "-DCMAKE_CUDA_ARCHITECTURES=75;80;86;89;90"
  ];

  meta = {
    description = "Riva-compatible NeMo-Speech.cpp ASR and diarization server";
    platforms = [ "aarch64-darwin" "x86_64-linux" ];
    license = lib.licenses.asl20;
  };
}
