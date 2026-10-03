import * as ImagePicker from "expo-image-picker";
import { useState } from "react";
import { Alert, SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";
import { scanMedication, scanReceipt } from "../api";
import LoadingButton from "../components/LoadingButton";
import { colors } from "../theme";

async function pickImage() {
  return new Promise((resolve) => {
    Alert.alert("Add a photo", "Take a new photo or choose one from your library?", [
      {
        text: "Camera",
        onPress: async () => {
          const permission = await ImagePicker.requestCameraPermissionsAsync();
          if (!permission.granted) {
            Alert.alert("Camera access needed", "Enable camera access in Settings to take a photo.");
            resolve(null);
            return;
          }
          const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
          resolve(result.canceled ? null : result.assets[0]);
        },
      },
      {
        text: "Photo Library",
        onPress: async () => {
          const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
          if (!permission.granted) {
            Alert.alert("Photo access needed", "Enable photo library access in Settings to choose a photo.");
            resolve(null);
            return;
          }
          const result = await ImagePicker.launchImageLibraryAsync({ quality: 0.8 });
          resolve(result.canceled ? null : result.assets[0]);
        },
      },
      { text: "Cancel", style: "cancel", onPress: () => resolve(null) },
    ]);
  });
}

export default function HomeScreen({ knownMedications, knownGroceries, onResults, error }) {
  const [scanningReceipt, setScanningReceipt] = useState(false);
  const [scanningMedication, setScanningMedication] = useState(false);

  const handleScanReceipt = async () => {
    const asset = await pickImage();
    if (!asset) return;

    setScanningReceipt(true);
    try {
      const data = await scanReceipt(asset, knownMedications);
      onResults({ mode: "grocery", ...data });
    } catch (err) {
      Alert.alert("Scan failed", err.message);
    } finally {
      setScanningReceipt(false);
    }
  };

  const handleScanMedication = async () => {
    const asset = await pickImage();
    if (!asset) return;

    setScanningMedication(true);
    try {
      const data = await scanMedication(asset, knownGroceries);
      onResults({ mode: "medication", ...data });
    } catch (err) {
      Alert.alert("Scan failed", err.message);
    } finally {
      setScanningMedication(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>⏳ XpireScan</Text>
        <Text style={styles.subtitle}>
          Scan a receipt or medication label to track expiration dates - or turn
          soon-to-expire groceries into a recipe.
        </Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>🛒 Scan a Receipt</Text>
          <LoadingButton
            label="Scan Receipt"
            loadingLabel="Scanning receipt..."
            loading={scanningReceipt}
            onPress={handleScanReceipt}
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>💊 Scan a Medication Label</Text>
          <LoadingButton
            label="Scan Medication"
            loadingLabel="Scanning label..."
            loading={scanningMedication}
            onPress={handleScanMedication}
            variant="secondary"
          />
        </View>

        <Text style={styles.hint}>
          Scanning runs OCR and an AI model, so it may take a few seconds.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  container: {
    padding: 20,
    paddingTop: 32,
  },
  title: {
    color: colors.text,
    fontSize: 26,
    fontWeight: "800",
    marginBottom: 4,
  },
  subtitle: {
    color: colors.muted,
    fontSize: 14,
    marginBottom: 28,
    lineHeight: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "700",
    marginBottom: 10,
  },
  hint: {
    color: colors.muted,
    fontSize: 13,
    marginTop: 8,
  },
  error: {
    color: colors.urgent,
    backgroundColor: "#3a1a1a",
    borderColor: "#5c2a2a",
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 20,
  },
});
