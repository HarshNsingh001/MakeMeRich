import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

export default function AlertsScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.header}>Alerts & Notifications</Text>
      
      <View style={styles.card}>
        <View style={styles.row}>
          <Text style={styles.title}>RELIANCE Price Target</Text>
          <Text style={styles.time}>2m ago</Text>
        </View>
        <Text style={styles.desc}>
          RELIANCE has crossed your alert threshold of ₹2,900.
        </Text>
      </View>
      
      <View style={[styles.card, { opacity: 0.7 }]}>
        <View style={styles.row}>
          <Text style={styles.title}>TCS Opportunity HIGH</Text>
          <Text style={styles.time}>1d ago</Text>
        </View>
        <Text style={styles.desc}>
          AI Analysis generated a HIGH opportunity signal for TCS.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary, padding: 20 },
  header: { fontSize: 24, fontWeight: 'bold', color: colors.textPrimary, marginBottom: 20 },
  card: { backgroundColor: colors.bgCard, padding: 16, borderRadius: 12, borderWidth: 1, borderColor: colors.borderLight, marginBottom: 12 },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  title: { color: colors.textPrimary, fontWeight: 'bold', fontSize: 16 },
  time: { color: colors.textMuted, fontSize: 12 },
  desc: { color: colors.textSecondary, lineHeight: 20 }
});
