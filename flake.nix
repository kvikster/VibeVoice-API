{
  description = "Nemotron, Sortformer, and ai-coustics LiveKit gateway";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
    };
  };

  outputs = { self, nixpkgs, pyproject-nix, uv2nix, pyproject-build-systems, ... }:
    let
      systems = [ "aarch64-darwin" "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      workspace = uv2nix.lib.workspace.loadWorkspace {
        workspaceRoot = ./voice_agent;
      };
    in {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true; # ai-coustics SDK and optional CUDA
          };
          pythonBase = pkgs.callPackage pyproject-nix.build.packages {
            python = pkgs.python312;
          };
          pythonSet = pythonBase.overrideScope (pkgs.lib.composeManyExtensions [
            pyproject-build-systems.overlays.wheel
            (workspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
          ]);
          gatewayEnv = pythonSet.mkVirtualEnv "callevate-gateway-env" {
            "local-voice-agent" = [ "aic" ];
          };
          models = import ./nix/models.nix { inherit pkgs; };
          mkBundle = cuda:
            let
              riva = import ./nix/riva.nix { inherit pkgs cuda; };
              gpu = if pkgs.stdenv.hostPlatform.isDarwin || cuda then 0 else -1;
              config = pkgs.writeText "callevate-riva-asr.yaml" ''
                asr:
                  backend:
                    gpu: ${toString gpu}
                  model:
                    path: ${models}/share/callevate/models/nemotron.gguf
                  streaming:
                    rnnt_right_context: 1
                  endpointing:
                    enable: true
                    vad_based: false
                    stop_history_eou_ms: 700
                  diar:
                    model_path: ${models}/share/callevate/models/sortformer.gguf
                    preset: streaming
              '';
              rivaCommand = pkgs.writeShellApplication {
                name = "callevate-riva";
                text = ''
                  exec ${riva}/bin/riva_server --config ${config} --bind "''${RIVA_BIND:-127.0.0.1:50051}" "$@"
                '';
              };
              gatewayCommand = pkgs.writeShellApplication {
                name = "callevate-gateway";
                text = ''
                  export RIVA_SERVER="''${RIVA_SERVER:-127.0.0.1:50051}"
                  export GATEWAY_STT_ENABLED="''${GATEWAY_STT_ENABLED:-1}"
                  exec ${gatewayEnv}/bin/bargein-server "$@"
                '';
              };
              smokeCommand = pkgs.writeShellApplication {
                name = "callevate-smoke";
                text = ''
                  exec ${gatewayEnv}/bin/python ${./nix/smoke.py} "$@"
                '';
              };
              stackCommand = pkgs.writeShellApplication {
                name = "callevate-stack";
                text = ''
                  ${rivaCommand}/bin/callevate-riva &
                  riva_pid=$!
                  ${gatewayCommand}/bin/callevate-gateway &
                  gateway_pid=$!
                  trap 'kill "$riva_pid" "$gateway_pid" 2>/dev/null || true' EXIT
                  wait -n "$riva_pid" "$gateway_pid"
                '';
              };
            in pkgs.symlinkJoin {
              name = "callevate-nemotron-gateway${if cuda then "-cuda" else ""}";
              paths = [ riva models rivaCommand gatewayCommand stackCommand smokeCommand ];
              meta.description = "Offline Nemotron/Sortformer models, Riva server, and LiveKit gateway";
            };
          defaultBundle = mkBundle false;
        in {
          default = defaultBundle;
          gateway-stack = defaultBundle;
          riva = import ./nix/riva.nix { inherit pkgs; cuda = false; };
          models = models;
        } // pkgs.lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux {
          gateway-stack-cuda = mkBundle true;
        }
      );
      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/callevate-stack";
        };
      });
    };
}
