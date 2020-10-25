with import <nixpkgs> {};
stdenv.mkDerivation {
  name = "coronaampel-dresden";
  buildInputs = with pkgs; [
    git
    python3Packages.opencv4
    python3Packages.selenium
    python3Packages.scikitimage
  ];
}
