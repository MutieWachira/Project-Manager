import { useEffect, useState } from 'react';
import { ActivityIndicator, Modal, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { SymbolView } from 'expo-symbols';

import Colors from '@/constants/Colors';
import { Text } from '@/components/Themed';
import { useColorScheme } from '@/components/useColorScheme';

const notes = [
  'A redesigned mobile command center with live project metrics and refresh controls.',
  'Improved project cards, status presentation, and empty states.',
  'A persistent “What’s new” experience for future mobile releases.',
];

export default function WhatsNew({ userId, version }: { userId: string; version: string }) {
  const theme = Colors[useColorScheme()];
  const [isOpen, setIsOpen] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const storageKey = `sherlskyycommand:last-seen-release:${userId}`;

  useEffect(() => {
    let active = true;
    async function checkRelease() {
      try {
        const seenVersion = await SecureStore.getItemAsync(storageKey);
        if (!active) return;
        if (seenVersion === null) await SecureStore.setItemAsync(storageKey, version);
        else setIsOpen(seenVersion !== version);
      } catch {
        // The sheet remains available even when persistence is unavailable.
      } finally {
        if (active) setIsChecking(false);
      }
    }
    void checkRelease();
    return () => { active = false; };
  }, [storageKey, version]);

  async function dismiss() {
    setIsOpen(false);
    try { await SecureStore.setItemAsync(storageKey, version); } catch {}
  }

  return (
    <>
      <Pressable accessibilityRole="button" accessibilityLabel="View what is new in this release" onPress={() => setIsOpen(true)} style={({ pressed }) => [styles.trigger, { backgroundColor: `${theme.tint}14`, borderColor: `${theme.tint}35`, opacity: pressed ? 0.72 : 1 }]}>
        {isChecking ? <ActivityIndicator size="small" color={theme.tint} /> : <SymbolView name={{ ios: 'sparkles', android: 'auto_awesome', web: 'auto_awesome' }} tintColor={theme.tint} size={16} />}
        <Text style={[styles.triggerText, { color: theme.tint }]}>What&apos;s new · {version}</Text>
      </Pressable>

      <Modal visible={isOpen} transparent animationType="fade" onRequestClose={() => void dismiss()}>
        <View style={styles.overlay}>
          <View style={[styles.sheet, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <View style={styles.sheetHeader}>
              <View style={styles.releaseMark}><SymbolView name={{ ios: 'sparkles', android: 'auto_awesome', web: 'auto_awesome' }} tintColor="#FFFFFF" size={21} /></View>
              <Pressable accessibilityRole="button" accessibilityLabel="Close release notes" onPress={() => void dismiss()} style={styles.closeButton}><SymbolView name={{ ios: 'xmark', android: 'close', web: 'close' }} tintColor={theme.muted} size={19} /></Pressable>
            </View>
            <Text style={[styles.eyebrow, { color: theme.tint }]}>MOBILE APPLICATION RELEASE</Text>
            <Text style={styles.title}>What&apos;s new</Text>
            <Text style={[styles.version, { color: theme.muted }]}>Version {version}</Text>
            <ScrollView style={styles.notes} showsVerticalScrollIndicator={false}>
              {notes.map((note) => <View key={note} style={styles.note}><View style={[styles.noteDot, { backgroundColor: theme.tint }]} /><Text style={[styles.noteText, { color: theme.text }]}>{note}</Text></View>)}
            </ScrollView>
            <Pressable accessibilityRole="button" onPress={() => void dismiss()} style={({ pressed }) => [styles.primaryButton, { backgroundColor: theme.tint, opacity: pressed ? 0.82 : 1 }]}><Text style={styles.primaryButtonText}>Got it</Text></Pressable>
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: { alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 7, borderWidth: 1, borderRadius: 12, paddingHorizontal: 11, paddingVertical: 9 },
  triggerText: { fontSize: 12, fontWeight: '800' }, overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: '#020617B8', padding: 16 }, sheet: { maxHeight: '76%', borderWidth: 1, borderRadius: 28, padding: 22 },
  sheetHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }, releaseMark: { width: 43, height: 43, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: '#2563EB' }, closeButton: { width: 38, height: 38, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: '#64748B16' },
  eyebrow: { fontSize: 10, fontWeight: '800', letterSpacing: 1.3 }, title: { fontSize: 28, fontWeight: '800', marginTop: 7 }, version: { fontSize: 13, marginTop: 5 }, notes: { marginTop: 23, maxHeight: 230 }, note: { flexDirection: 'row', gap: 11, paddingBottom: 16 }, noteDot: { width: 7, height: 7, borderRadius: 4, marginTop: 6 }, noteText: { flex: 1, fontSize: 14, lineHeight: 21 }, primaryButton: { alignItems: 'center', borderRadius: 14, marginTop: 8, paddingVertical: 14 }, primaryButtonText: { color: '#FFFFFF', fontSize: 14, fontWeight: '800' },
});
